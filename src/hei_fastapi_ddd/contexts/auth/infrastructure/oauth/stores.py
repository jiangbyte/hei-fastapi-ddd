""" Author: Charlie

OAuth 一次性存储：state（授权状态）与 exchange（登录兑换码），基于 Redis。

- state: 保存授权意图（账号类型/意图/提供商/账号ID/跳转地址），TTL 10 分钟。
- exchange: 保存登录结果，避免把 token 放进前端回调 URL，TTL 2 分钟。
"""
import json
import secrets
from dataclasses import asdict, dataclass
from typing import Any

from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.redis.redis import get_redis

STATE_TTL_SECONDS = 10 * 60
EXCHANGE_TTL_SECONDS = 2 * 60


def _state_key(state: str) -> str:
    return f"oauth:state:{state}"


def _exchange_key(code: str) -> str:
    return f"oauth:exchange:{code}"


def _required_redis() -> Any:
    """获取 Redis 客户端，未初始化时抛业务错误。"""
    redis = get_redis()
    if redis is None:
        raise BusinessError("Redis is required for OAuth flow")
    return redis


def _decode(value: bytes | str | None) -> str | None:
    if value is None:
        return None
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


@dataclass(slots=True)
class OauthStatePayload:
    """OAuth state 载荷（存 Redis，一次性消费）。"""

    account_type: str
    intent: str
    provider: str
    account_id: str | None = None
    redirect: str | None = None


class OauthStateStore:
    """OAuth state 一次性存储。"""

    async def save(self, payload: OauthStatePayload) -> str:
        """保存授权状态，返回一次性 state。"""
        redis = _required_redis()
        state = secrets.token_urlsafe(24)
        await redis.setex(_state_key(state), STATE_TTL_SECONDS, json.dumps(asdict(payload)))
        return state

    async def consume(self, state: str | None) -> OauthStatePayload | None:
        """消费授权状态（getdel），无效或过期返回 None。"""
        if not state or not state.strip():
            return None
        redis = _required_redis()
        raw = _decode(await redis.getdel(_state_key(state.strip())))
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return OauthStatePayload(
                account_type=str(data.get("account_type") or ""),
                intent=str(data.get("intent") or "LOGIN"),
                provider=str(data.get("provider") or ""),
                account_id=data.get("account_id"),
                redirect=data.get("redirect"),
            )
        except (ValueError, TypeError):
            return None


class OauthExchangeStore:
    """OAuth 登录一次性兑换码存储。"""

    async def save(self, login_result: dict[str, Any]) -> str:
        """保存登录结果，返回一次性兑换码。"""
        token = login_result.get("token")
        if not token:
            raise BusinessError("登录结果无效")
        redis = _required_redis()
        code = secrets.token_urlsafe(24)
        await redis.setex(_exchange_key(code), EXCHANGE_TTL_SECONDS, json.dumps(login_result))
        return code

    async def consume(self, code: str | None) -> dict[str, Any]:
        """消费兑换码并返回登录结果，无效或过期抛业务错误。"""
        if not code or not code.strip():
            raise BusinessError("兑换码无效或已过期")
        redis = _required_redis()
        raw = _decode(await redis.getdel(_exchange_key(code.strip())))
        if not raw:
            raise BusinessError("兑换码无效或已过期")
        try:
            result = json.loads(raw)
            if not isinstance(result, dict) or not result.get("token"):
                raise ValueError("invalid payload")
            return result
        except (ValueError, TypeError) as exc:
            raise BusinessError("兑换码无效或已过期") from exc
