""" Author: Charlie

认证依赖：解析登录会话、当前账户，并生成账户类型/权限校验依赖。
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.observability.context import account_id_ctx, account_type_ctx
from hei_fastapi_ddd.shared.security.account_type import assert_account_type_allowed
from hei_fastapi_ddd.shared.security.permission import PermissionChecker
from hei_fastapi_ddd.shared.security.permission_registry import (
    ACCOUNT_TYPE_META_ATTR,
    PERMISSION_META_ATTR,
)
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.security.session_auth import resolve_request_session
from hei_fastapi_ddd.types.business import AuthenticationError, AuthorizationError


async def get_current_session(request: Request) -> SessionPayload:
    """解析登录会话（Cookie 优先；与 AuthWhitelistMiddleware 共用逻辑）。"""
    session = await resolve_request_session(request, required=True)
    assert session is not None
    return session


async def get_optional_session(request: Request) -> SessionPayload | None:
    """可选登录会话：缺失或无效 token 时返回 None。"""
    try:
        return await resolve_request_session(request, required=False)
    except AuthenticationError:
        return None


async def get_current_account(
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """解析并校验当前账户，同时写入账户上下文。"""
    account_id_ctx.set(session.account_id)
    account_type_ctx.set(session.account_type)
    from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import (
        AccountRepository,
    )

    account = await AccountRepository(db).get_account_by_id(session.account_id)
    if (
        not account
        or account.cancelled_at is not None
        or account.account_status != AccountStatusEnum.ENABLED.value
    ):
        raise AuthenticationError("Account is inactive or missing")
    return account


def require_account_type(*account_types: AccountType):
    """基于账户类型枚举生成依赖校验函数。"""

    async def dependency(
        session: Annotated[SessionPayload, Depends(get_current_session)],
        account=Depends(get_current_account),
    ) -> SessionPayload:
        assert_account_type_allowed(session.account_type, set(account_types))
        return session

    setattr(
        dependency,
        ACCOUNT_TYPE_META_ATTR,
        {"account_types": [account_type.value for account_type in account_types]},
    )
    return dependency


def require_permission(permission_code: str):
    """基于权限码生成依赖校验函数。"""

    async def dependency(
        session: Annotated[SessionPayload, Depends(get_current_session)],
        account=Depends(get_current_account),
    ) -> SessionPayload:
        if not PermissionChecker.has_permission(session.permission_keys, permission_code):
            raise AuthorizationError(f"Permission denied: {permission_code}")
        return session

    setattr(dependency, PERMISSION_META_ATTR, {"permission_key": permission_code})
    return dependency
