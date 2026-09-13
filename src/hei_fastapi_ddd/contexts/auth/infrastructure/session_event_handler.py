""" Author: Charlie

账户会话下游处理器：响应 IAM 领域集成事件，刷新或删除 Redis 会话。
"""

from __future__ import annotations

from hei_fastapi_ddd.contexts.auth.application.session_service import AccountSessionService
from hei_fastapi_ddd.shared.messaging import subscribe
from hei_fastapi_ddd.shared.persistence.session import get_session_factory


async def _handle_authorization_changed(*, account_ids: list[str], **_: object) -> None:
    """授权变更后刷新在线会话投影。"""
    # 1. 无账户 ID 则直接返回
    if not account_ids:
        return
    # 2. 打开独立会话执行刷新，避免占用调用方事务
    factory = get_session_factory()
    async with factory() as db:
        await AccountSessionService(db).refresh_accounts_sessions(sorted(set(account_ids)))


async def _handle_accounts_sessions_deleted(
    *,
    session_targets: list[tuple[str, str]],
    **_: object,
) -> None:
    """账户删除/清理后踢掉对应在线会话。"""
    # 1. 无目标则跳过
    if not session_targets:
        return
    # 2. 独立会话执行删除
    factory = get_session_factory()
    async with factory() as db:
        await AccountSessionService(db).delete_accounts_sessions(session_targets)


def register() -> None:
    """注册会话相关集成事件订阅。"""
    subscribe("on_authorization_changed", _handle_authorization_changed)
    subscribe("on_accounts_sessions_deleted", _handle_accounts_sessions_deleted)
