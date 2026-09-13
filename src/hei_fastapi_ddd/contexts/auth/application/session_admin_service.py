""" Author: Charlie

会话管理服务：统计在线会话、分页聚合账户维度信息并支持强制下线。
"""

from collections import Counter
from datetime import UTC, datetime, timedelta
from time import monotonic

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.auth.interfaces.http.session_schemas import (
    SessionAccountItem,
    SessionAnalysisResponse,
    SessionPageQuery,
    SessionTokenInfo,
    SessionTokensQuery,
)
from hei_fastapi_ddd.contexts.iam.application.account.query_service import AccountQueryService
from hei_fastapi_ddd.contexts.iam.application.api.account_api_adapter import (
    AccountApiAdapter as AccountRepository,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page

_ANALYSIS_CACHE_TTL_SECONDS = 30.0
_analysis_cache: tuple[float, SessionAnalysisResponse] | None = None


def _mask_token(token: str | None) -> str:
    """token 脱敏：前 4 后 4，中间 ****。"""
    if not token or not str(token).strip():
        return ""
    value = str(token).strip()
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


class SessionAdminService:
    """会话管理服务：在线会话分析、分页与强制下线。"""

    def __init__(self, db: AsyncSession) -> None:
        """初始化账户仓储。"""
        self.db = db
        self.account_repo = AccountRepository(db)

    async def analysis(self) -> SessionAnalysisResponse:
        """统计在线账户、token 与近一小时新增等指标。"""
        global _analysis_cache
        now_mono = monotonic()
        if _analysis_cache is not None and _analysis_cache[0] > now_mono:
            return _analysis_cache[1]

        grouped = await self._group_online_sessions()
        token_counts = [len(items) for items in grouped.values()]
        now = datetime.now(UTC)
        one_hour_ago = now - timedelta(hours=1)
        one_hour_new_count = 0
        for sessions in grouped.values():
            for session in sessions:
                login_at = _parse_datetime(session.login_at)
                if login_at and login_at >= one_hour_ago:
                    one_hour_new_count += 1
        account_types = Counter(account_type for account_type, _ in grouped)
        result = SessionAnalysisResponse(
            online_account_count=len(grouped),
            online_token_count=sum(token_counts),
            admin_account_count=account_types.get(AccountType.ADMIN.value, 0),
            portal_account_count=account_types.get(AccountType.PORTAL.value, 0),
            one_hour_new_count=one_hour_new_count,
            max_token_count=max(token_counts, default=0),
        )
        _analysis_cache = (now_mono + _ANALYSIS_CACHE_TTL_SECONDS, result)
        return result

    async def page(self, query: SessionPageQuery) -> PageData[SessionAccountItem]:
        """按账户维度分页返回在线会话。"""
        grouped = await self._group_online_sessions()
        grouped = self._filter_grouped(grouped, query)
        needs_profile = bool(query.account or query.keyword)
        if needs_profile:
            items = await self._build_items(grouped)
            items = self._filter_profile_items(items, query)
            items.sort(key=self._sort_key, reverse=True)
            total = len(items)
            page_items = items[query.offset : query.offset + query.size]
            return build_page(query, total, page_items)

        sorted_keys = sorted(grouped.keys(), key=lambda key: self._group_sort_key(grouped[key]), reverse=True)
        total = len(sorted_keys)
        page_keys = sorted_keys[query.offset : query.offset + query.size]
        page_grouped = {key: grouped[key] for key in page_keys}
        page_items = await self._build_items(page_grouped)
        page_items.sort(key=self._sort_key, reverse=True)
        return build_page(query, total, page_items)

    async def tokens(self, query: SessionTokensQuery) -> list[SessionTokenInfo]:
        """返回指定账户的在线 token 详情列表（account_type 缺省按 ADMIN）。"""
        account_type = query.account_type or AccountType.ADMIN
        tokens = await session_store.get_account_tokens(account_type.value, query.account_id)
        sessions = await session_store.list_sessions_by_tokens(tokens)
        return [_token_info(session) for session in sessions]

    async def exit_sessions(self, targets: list[SessionTokensQuery]) -> None:
        """批量删除指定账户的全部会话（account_type 缺省按 ADMIN）。"""
        labels: list[str] = []
        pairs: list[tuple[str, str]] = []
        for target in targets:
            account_type = target.account_type or AccountType.ADMIN
            account_id = target.account_id
            pairs.append((account_type.value, account_id))
            labels.append(f"{account_id}（{account_type.value}）")
        audit_snapshots.after({"账号": labels})
        await session_store.delete_accounts_sessions(pairs)

    async def exit_tokens(self, tokens: list[str]) -> None:
        """批量删除指定 token 的会话（去重后逐个删除）。"""
        unique_tokens = list(dict.fromkeys(tokens))
        masked_tokens = [_mask_token(token) for token in unique_tokens if token and str(token).strip()]
        audit_snapshots.after({"会话": masked_tokens})
        for token in unique_tokens:
            await session_store.delete(token)

    async def _group_online_sessions(self) -> dict[tuple[str, str], list[SessionPayload]]:
        """拉取全部会话并按（账户类型, 账户 ID）分组。"""
        tokens = await session_store.list_tokens()
        sessions = await session_store.list_sessions_by_tokens(tokens)
        grouped: dict[tuple[str, str], list[SessionPayload]] = {}
        for session in sessions:
            grouped.setdefault((str(session.account_type), session.account_id), []).append(session)
        return grouped

    def _filter_grouped(
        self,
        grouped: dict[tuple[str, str], list[SessionPayload]],
        query: SessionPageQuery,
    ) -> dict[tuple[str, str], list[SessionPayload]]:
        """仅用会话载荷可判定的条件过滤（账户类型 / ID / IP）。"""
        result = grouped
        if query.account_type:
            wanted = query.account_type.value
            result = {
                key: sessions
                for key, sessions in result.items()
                if key[0] == wanted
            }
        if query.account_id:
            result = {
                key: sessions
                for key, sessions in result.items()
                if key[1] == query.account_id
            }
        if query.ip:
            result = {
                key: sessions
                for key, sessions in result.items()
                if any(query.ip in str(session.client_ip or "") for session in sessions)
            }
        return result

    async def _build_items(
        self,
        grouped: dict[tuple[str, str], list[SessionPayload]],
    ) -> list[SessionAccountItem]:
        """把分组会话聚合为账户维度的展示项。"""
        if not grouped:
            return []
        account_ids = [account_id for _, account_id in grouped]
        accounts = await self.account_repo.list_accounts_by_ids(account_ids)
        schema_map = {
            schema.id: schema
            for schema in await AccountQueryService(self.db).build_account_picker_schemas(accounts)
        }
        account_map = {account.id: account for account in accounts}
        items: list[SessionAccountItem] = []
        for (account_type, account_id), sessions in grouped.items():
            schema = schema_map.get(account_id)
            account = account_map.get(account_id)
            token_infos = [_token_info(session) for session in sessions]
            token_infos.sort(
                key=lambda item: (
                    item.last_active_at or item.login_at or datetime.min.replace(tzinfo=UTC)
                ),
                reverse=True,
            )
            login_times = [item.login_at for item in token_infos if item.login_at]
            active_times = [item.last_active_at for item in token_infos if item.last_active_at]
            newest = token_infos[0] if token_infos else None
            items.append(
                SessionAccountItem(
                    account_id=account_id,
                    account_type=account_type,
                    account=getattr(schema, "account", None) or "",
                    name=getattr(schema, "name", None),
                    latest_login_ip=getattr(account, "latest_login_ip", None),
                    latest_login_time=getattr(account, "latest_login_time", None),
                    client_ip=newest.client_ip if newest else None,
                    device_label=newest.device_label if newest else None,
                    token_count=len(token_infos),
                    first_login_at=min(login_times) if login_times else None,
                    latest_active_at=max(active_times) if active_times else None,
                    tokens=token_infos,
                )
            )
        return items

    def _filter_profile_items(
        self,
        items: list[SessionAccountItem],
        query: SessionPageQuery,
    ) -> list[SessionAccountItem]:
        """按账号名 / 昵称等资料字段过滤。"""
        result = items
        if query.account:
            keyword = query.account.lower()
            result = [
                item
                for item in result
                if keyword in item.account.lower()
                or keyword in str(item.name or "").lower()
                or keyword in str(item.nickname or "").lower()
            ]
        if query.keyword:
            keyword = query.keyword.lower()
            result = [
                item
                for item in result
                if keyword in item.account.lower()
                or keyword in item.account_id.lower()
            ]
        return result

    def _group_sort_key(self, sessions: list[SessionPayload]) -> tuple[datetime, str]:
        """分组排序键：最近活跃时间。"""
        latest = datetime.min.replace(tzinfo=UTC)
        account_id = sessions[0].account_id if sessions else ""
        for session in sessions:
            active = _parse_datetime(session.last_active_at) or _parse_datetime(session.login_at)
            if active and active > latest:
                latest = active
        return latest, account_id

    def _sort_key(self, item: SessionAccountItem) -> tuple[datetime, str]:
        """会话项排序键：最近活跃时间 + 账户 ID。"""
        active_at = item.latest_active_at or item.first_login_at or datetime.min.replace(tzinfo=UTC)
        if active_at.tzinfo is None:
            active_at = active_at.replace(tzinfo=UTC)
        return active_at, item.account_id


def _token_info(session: SessionPayload) -> SessionTokenInfo:
    """把会话载荷转换为 token 信息模型。"""
    return SessionTokenInfo(
        token=session.token,
        account_id=session.account_id,
        account_type=session.account_type,
        remember_me=session.remember_me,
        device_label=session.device_label,
        client_ip=session.client_ip,
        user_agent=session.user_agent,
        login_at=_parse_datetime(session.login_at),
        last_active_at=_parse_datetime(session.last_active_at),
        expires_at=_parse_datetime(session.expires_at),
    )


def _parse_datetime(value: str | None) -> datetime | None:
    """解析 ISO 时间字符串，失败返回 None。"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
