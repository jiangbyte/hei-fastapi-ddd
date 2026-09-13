""" Author: Charlie

会话存储：基于 Redis 保存登录会话载荷，并提供 token 反向索引、
空闲超时、并发会话裁剪与授权变更后的批量刷新能力。

会话以 JSON 形式存于 Redis，账户维度维护 token 集合以便统一踢下线。
"""

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TypedDict

from hei_fastapi_ddd.shared.config.enums import AccountType, DataScope
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.redis.keys import (
    login_account_tokens_key,
    login_token_key,
    login_tokens_key,
)
from hei_fastapi_ddd.shared.redis.redis import get_redis

logger = logging.getLogger(__name__)


class PermissionGrantPayload(TypedDict):
    """会话中缓存的权限项结构，避免使用无约束的裸字典。"""

    permission_key: str
    data_scope: DataScope | str
    custom_scope_dept_ids: list[str]
    source_type: str
    source_id: str


@dataclass(slots=True)
class SessionPayload:
    """登录会话载荷，保存鉴权与数据权限判断所需的最小上下文。"""

    token: str
    account_id: str
    account_type: AccountType | str
    role_ids: list[str] = field(default_factory=list)
    dept_ids: list[str] = field(default_factory=list)
    group_ids: list[str] = field(default_factory=list)
    resource_ids: list[str] = field(default_factory=list)
    permission_keys: list[str] = field(default_factory=list)
    permission_grants: list[PermissionGrantPayload] = field(default_factory=list)
    client_resource_ids: list[str] = field(default_factory=list)
    client_permission_keys: list[str] = field(default_factory=list)
    client_ip: str | None = None
    user_agent: str | None = None
    remember_me: bool = True
    password_expired: bool = False
    force_bind_email: bool = False
    force_bind_phone: bool = False
    device_label: str | None = None
    login_at: str | None = None
    last_active_at: str | None = None
    expires_at: str | None = None


class SessionStore:
    """会话存储门面，Redis 是运行必需依赖。"""

    async def set(self, payload: SessionPayload, ttl_seconds: int) -> None:
        """写入登录会话，并同步维护用户到 token 的反向索引。"""
        data = asdict(payload)
        redis = self._get_required_redis()
        await redis.setex(login_token_key(payload.token), ttl_seconds, json.dumps(data))
        await redis.sadd(
            login_account_tokens_key(str(payload.account_type), payload.account_id),
            payload.token,
        )
        await redis.sadd(login_tokens_key(), payload.token)

    async def get(self, token: str) -> SessionPayload | None:
        """按 token 从 Redis 读取会话。"""
        redis = self._get_required_redis()
        session = await self._load_raw(redis, token)
        if session is None:
            return None
        return await self._check_idle_timeout(redis, session)

    async def touch(self, token: str) -> None:
        """异步更新 last_active_at 并滑动 TTL。"""
        try:
            redis = self._get_required_redis()
            raw = await redis.get(login_token_key(token))
            if not raw:
                return
            raw_text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            data = json.loads(raw_text)
            data["last_active_at"] = datetime.now(UTC).isoformat()
            remember_me = data.get("remember_me", True)
            ttl = (
                settings.auth.token_ttl_seconds
                if remember_me
                else settings.auth.token_ttl_short_seconds
            )
            await redis.setex(login_token_key(token), ttl, json.dumps(data))
        except Exception:
            logger.debug("Failed to touch session %s", token[:8], exc_info=True)

    async def list_account_sessions(
        self,
        account_type: str,
        account_id: str,
    ) -> list[SessionPayload]:
        """返回账户全部在线会话，按登录时间升序。"""
        tokens = await self.get_account_tokens(account_type, account_id)
        sessions = await self.list_sessions_by_tokens(tokens)
        sessions.sort(key=lambda s: _parse_datetime_or_epoch(s.login_at))
        return sessions

    async def prune_excess_sessions(
        self,
        account_type: str,
        account_id: str,
        max_sessions: int,
    ) -> None:
        """超过 max_sessions 时移除最旧会话。"""
        if max_sessions <= 0:
            return
        sessions = await self.list_account_sessions(account_type, account_id)
        if len(sessions) <= max_sessions:
            return
        excess = sessions[:-max_sessions]
        for session in excess:
            await self.delete(session.token)
        logger.info("Pruned %d excess sessions for %s/%s", len(excess), account_type, account_id)

    async def _check_idle_timeout(self, redis, session: SessionPayload) -> SessionPayload | None:
        """空闲超时则删除会话。"""
        idle_timeout = settings.auth.session_idle_timeout_seconds
        if idle_timeout <= 0 or not session.last_active_at:
            return session
        last_active = _parse_datetime_or_epoch(session.last_active_at)
        if (datetime.now(UTC) - last_active).total_seconds() > idle_timeout:
            logger.info("Session %s idle timeout, deleting", session.token[:8])
            await self.delete(session.token)
            return None
        return session

    async def get_account_tokens(self, account_type: str, account_id: str) -> list[str]:
        """读取指定账户当前在线 token 列表，用于授权变更后刷新会话权限。"""
        token_map = await self.get_accounts_tokens([(account_type, account_id)])
        return token_map.get((account_type, account_id), [])

    async def list_tokens(self) -> list[str]:
        """读取全局在线 token 索引，包含待清理的过期残留。"""
        redis = self._get_required_redis()
        values = await redis.smembers(login_tokens_key())
        return [
            value.decode("utf-8") if isinstance(value, bytes) else str(value) for value in values
        ]

    async def count_tokens(self) -> int:
        """统计全局在线 token 索引数量（含可能过期残留，用于仪表盘近似在线数）。"""
        redis = self._get_required_redis()
        return int(await redis.scard(login_tokens_key()) or 0)

    async def list_sessions_by_tokens(self, tokens: list[str]) -> list[SessionPayload]:
        """批量读取 token 会话（MGET），顺手清理全局索引里的过期 token。"""
        unique_tokens = list(dict.fromkeys(tokens))
        if not unique_tokens:
            return []
        redis = self._get_required_redis()
        raw_values = await self._get_many(
            redis, [login_token_key(token) for token in unique_tokens]
        )
        sessions: list[SessionPayload] = []
        stale_tokens: list[str] = []
        for token, raw in zip(unique_tokens, raw_values, strict=False):
            if raw is None:
                stale_tokens.append(token)
                continue
            raw_text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            try:
                data = json.loads(raw_text)
            except (ValueError, TypeError):
                stale_tokens.append(token)
                continue
            data.setdefault("client_resource_ids", [])
            data.setdefault("client_permission_keys", [])
            session = SessionPayload(**data)
            checked = await self._check_idle_timeout(redis, session)
            if checked is not None:
                sessions.append(checked)
            else:
                stale_tokens.append(token)
        if stale_tokens:
            await redis.srem(login_tokens_key(), *stale_tokens)
        return sessions

    async def get_accounts_tokens(
        self,
        targets: list[tuple[str, str]],
    ) -> dict[tuple[str, str], list[str]]:
        """批量读取账户在线 token，避免多账号授权刷新时逐账号访问 Redis。"""
        redis = self._get_required_redis()
        unique_targets = list(dict.fromkeys(targets))
        if not unique_targets:
            return {}
        rows = await self._smembers_many(
            redis,
            [
                login_account_tokens_key(account_type, account_id)
                for account_type, account_id in unique_targets
            ],
        )
        return {
            target: [
                value.decode("utf-8") if isinstance(value, bytes) else str(value)
                for value in values
            ]
            for target, values in zip(unique_targets, rows, strict=True)
        }

    async def refresh_account_sessions(
        self,
        account_type: str,
        account_id: str,
        payload_factory: Callable[[str, SessionPayload], Awaitable[SessionPayload]],
    ) -> None:
        """刷新某个账户所有在线会话中的授权上下文，保留原 token 不变。"""
        await self.refresh_accounts_sessions(
            [(account_type, account_id)],
            {(account_type, account_id): payload_factory},
        )

    async def refresh_accounts_sessions(
        self,
        targets: list[tuple[str, str]],
        payload_factories: dict[
            tuple[str, str], Callable[[str, SessionPayload], Awaitable[SessionPayload]]
        ],
    ) -> None:
        """批量刷新多个账户在线会话，Redis 读写合并为批量操作。"""
        unique_targets = [
            target for target in dict.fromkeys(targets) if target in payload_factories
        ]
        if not unique_targets:
            return
        redis = self._get_required_redis()
        token_map = await self.get_accounts_tokens(unique_targets)
        token_targets: list[tuple[str, tuple[str, str]]] = []
        for target in unique_targets:
            token_targets.extend((token, target) for token in token_map.get(target, []))
        if not token_targets:
            return

        existing_raw = await self._get_many(
            redis,
            [login_token_key(token) for token, _ in token_targets],
        )
        updates: list[tuple[SessionPayload, str]] = []
        for (token, target), raw in zip(token_targets, existing_raw, strict=True):
            if not raw:
                continue
            raw_text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            try:
                data = json.loads(raw_text)
            except (ValueError, TypeError):
                continue
            data.setdefault("client_resource_ids", [])
            data.setdefault("client_permission_keys", [])
            existing = SessionPayload(**data)
            refreshed = await payload_factories[target](token, existing)
            updates.append((refreshed, token))
        await self._set_sessions(redis, updates)

    async def delete(self, token: str) -> None:
        """删除会话，并在 Redis 模式下同步清理用户维度的 token 索引。"""
        redis = self._get_required_redis()
        # 必须用 _load_raw：经 get() 会再走空闲超时 → delete，造成无限递归。
        payload = await self._load_raw(redis, token)
        await self._delete_keys(redis, [login_token_key(token)])
        await redis.srem(login_tokens_key(), token)
        if payload:
            await redis.srem(
                login_account_tokens_key(str(payload.account_type), payload.account_id), token
            )

    async def _load_raw(self, redis, token: str) -> SessionPayload | None:
        """读取会话载荷，不做空闲超时校验。"""
        raw = await redis.get(login_token_key(token))
        if not raw:
            return None
        raw_text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        data = json.loads(raw_text)
        data.setdefault("client_resource_ids", [])
        data.setdefault("client_permission_keys", [])
        return SessionPayload(**data)

    async def delete_account_sessions(self, account_type: str, account_id: str) -> None:
        """删除指定账户的所有在线会话和账户维度 token 索引。"""
        await self.delete_accounts_sessions([(account_type, account_id)])

    async def delete_accounts_sessions(self, targets: list[tuple[str, str]]) -> None:
        """批量删除多个账户的所有在线会话和账户维度 token 索引。"""
        redis = self._get_required_redis()
        unique_targets = list(dict.fromkeys(targets))
        if not unique_targets:
            return
        token_map = await self.get_accounts_tokens(unique_targets)
        keys = {login_token_key(token) for tokens in token_map.values() for token in tokens}
        keys.update(
            login_account_tokens_key(account_type, account_id)
            for account_type, account_id in unique_targets
        )
        if keys:
            await self._delete_keys(redis, list(keys))
        tokens = {token for tokens in token_map.values() for token in tokens}
        if tokens:
            await redis.srem(login_tokens_key(), *tokens)

    async def _delete_keys(self, redis, keys: list[str]) -> None:
        """兼容真实 Redis 的多 key delete 和测试 FakeRedis 的单 key delete。"""
        unique_keys = list(dict.fromkeys(keys))
        if not unique_keys:
            return
        try:
            await redis.delete(*unique_keys)
        except TypeError:
            for key in unique_keys:
                await redis.delete(key)

    async def _smembers_many(self, redis, keys: list[str]) -> list[set]:
        """批量读取 Redis set；客户端不支持 pipeline 时退化为顺序读取。"""
        if not keys:
            return []
        pipeline_factory = getattr(redis, "pipeline", None)
        if pipeline_factory is None:
            return [await redis.smembers(key) for key in keys]
        pipe = pipeline_factory()
        for key in keys:
            pipe.smembers(key)
        return await pipe.execute()

    async def _get_many(self, redis, keys: list[str]) -> list[object | None]:
        """批量读取 Redis string；客户端不支持 mget 时退化为顺序读取。"""
        if not keys:
            return []
        mget = getattr(redis, "mget", None)
        if mget is None:
            return [await redis.get(key) for key in keys]
        return await mget(keys)

    async def _set_sessions(self, redis, updates: list[tuple[SessionPayload, str]]) -> None:
        """批量写入刷新后的会话并维护账户 token 索引。"""
        if not updates:
            return
        pipeline_factory = getattr(redis, "pipeline", None)
        if pipeline_factory is None:
            for refreshed, token in updates:
                await redis.setex(
                    login_token_key(token),
                    settings.auth.token_ttl_seconds,
                    json.dumps(asdict(refreshed)),
                )
                await redis.sadd(
                    login_account_tokens_key(
                        str(refreshed.account_type),
                        refreshed.account_id,
                    ),
                    token,
                )
                await redis.sadd(login_tokens_key(), token)
            return
        pipe = pipeline_factory()
        for refreshed, token in updates:
            pipe.setex(
                login_token_key(token),
                settings.auth.token_ttl_seconds,
                json.dumps(asdict(refreshed)),
            )
            pipe.sadd(
                login_account_tokens_key(
                    str(refreshed.account_type),
                    refreshed.account_id,
                ),
                token,
            )
            pipe.sadd(login_tokens_key(), token)
        await pipe.execute()

    def _get_required_redis(self):
        redis = get_redis()
        if redis is None:
            raise RuntimeError("Redis is required for session store")
        return redis


def _parse_datetime_or_epoch(value: str | None) -> datetime:
    """解析 ISO datetime 字符串；失败时返回 Unix 纪元。"""
    if not value:
        return datetime.min.replace(tzinfo=UTC)
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=UTC)


session_store = SessionStore()
