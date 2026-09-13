""" Author: Charlie

三方登录路由：管理端与门户端的授权/回调/兑换/绑定/解绑。
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.auth.application.oauth.oauth_application_service import (
    AuthOauthService,
)
from hei_fastapi_ddd.contexts.auth.interfaces.http.oauth_schemas import (
    AdminOauthUnbindRequest,
    OauthAuthorizeResult,
    OauthBindingResult,
    OauthExchangeRequest,
    WechatMpLoginRequest,
)
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_session,
    get_optional_session,
    require_permission,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

admin_router = APIRouter()
portal_router = APIRouter()

SessionDep = Annotated[SessionPayload, Depends(get_current_session)]
OptionalSessionDep = Annotated[SessionPayload | None, Depends(get_optional_session)]


def _oauth_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> AuthOauthService:
    """构造 OAuth 服务实例。"""
    return AuthOauthService(db)


ServiceDep = Annotated[AuthOauthService, Depends(_oauth_service)]


@admin_router.get(
    "/v1/admin/oauth/{provider}/authorize",
    response_model=ApiResponse[OauthAuthorizeResult],
)
async def admin_oauth_authorize(
    provider: str,
    service: ServiceDep,
    session: OptionalSessionDep,
    intent: str | None = None,
    redirect: str | None = None,
) -> ApiResponse[OauthAuthorizeResult]:
    """发起管理端三方登录/绑定授权。"""
    result = await service.authorize(
        AccountType.ADMIN, provider, intent, redirect, session
    )
    return success(OauthAuthorizeResult(**result))


@admin_router.get("/v1/admin/oauth/{provider}/callback")
async def admin_oauth_callback(
    provider: str,
    service: ServiceDep,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    """管理端三方登录回调：302 跳回前端回调页。"""
    location = await service.handle_callback(
        AccountType.ADMIN, provider, code, state
    )
    return RedirectResponse(url=location)


@admin_router.post(
    "/v1/admin/oauth/exchange",
    response_model=ApiResponse,
)
async def admin_oauth_exchange(
    payload: OauthExchangeRequest,
    service: ServiceDep,
) -> ApiResponse:
    """用一次性兑换码换取登录结果。"""
    return success(await service.exchange(payload.code))


@admin_router.get(
    "/v1/admin/oauth/bindings",
    response_model=ApiResponse[list[OauthBindingResult]],
)
async def admin_oauth_bindings(
    service: ServiceDep,
    session: SessionDep,
) -> ApiResponse[list[OauthBindingResult]]:
    """列出当前管理端账号三方绑定。"""
    return success(await service.list_current_bindings(session.account_id))


@admin_router.post(
    "/v1/admin/oauth/{provider}/bind/authorize",
    response_model=ApiResponse[OauthAuthorizeResult],
)
async def admin_oauth_bind_authorize(
    provider: str,
    service: ServiceDep,
    session: SessionDep,
) -> ApiResponse[OauthAuthorizeResult]:
    """发起管理端三方绑定授权。"""
    result = await service.bind_authorize(
        AccountType.ADMIN, provider, session
    )
    return success(OauthAuthorizeResult(**result))


@admin_router.post(
    "/v1/admin/oauth/{provider}/unbind",
    response_model=ApiResponse[None],
)
async def admin_oauth_unbind(
    provider: str,
    service: ServiceDep,
    session: SessionDep,
) -> ApiResponse[None]:
    """解绑当前管理端账号指定提供商。"""
    await service.unbind(session.account_id, provider)
    return success()


@admin_router.post(
    "/v1/admin/sys/accounts/oauth/unbind",
    dependencies=[Depends(require_permission("iam:account:update"))],
    response_model=ApiResponse[None],
)
async def admin_accounts_oauth_unbind(
    payload: AdminOauthUnbindRequest,
    service: ServiceDep,
) -> ApiResponse[None]:
    """管理端强制解绑指定账号的三方绑定。"""
    await service.admin_unbind(payload.account_id, payload.provider)
    return success()


# ------------------------------------------------------------------ portal

@portal_router.get(
    "/v1/portal/oauth/{provider}/authorize",
    response_model=ApiResponse[OauthAuthorizeResult],
)
async def portal_oauth_authorize(
    provider: str,
    service: ServiceDep,
    session: OptionalSessionDep,
    intent: str | None = None,
    redirect: str | None = None,
) -> ApiResponse[OauthAuthorizeResult]:
    """发起门户三方登录/绑定授权。"""
    result = await service.authorize(
        AccountType.PORTAL, provider, intent, redirect, session
    )
    return success(OauthAuthorizeResult(**result))


@portal_router.get("/v1/portal/oauth/{provider}/callback")
async def portal_oauth_callback(
    provider: str,
    service: ServiceDep,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    """门户三方登录回调：302 跳回前端回调页。"""
    location = await service.handle_callback(
        AccountType.PORTAL, provider, code, state
    )
    return RedirectResponse(url=location)


@portal_router.post(
    "/v1/portal/oauth/exchange",
    response_model=ApiResponse,
)
async def portal_oauth_exchange(
    payload: OauthExchangeRequest,
    service: ServiceDep,
) -> ApiResponse:
    """用一次性兑换码换取登录结果。"""
    return success(await service.exchange(payload.code))


@portal_router.post(
    "/v1/portal/oauth/wechat-mp/login",
    response_model=ApiResponse,
)
async def portal_oauth_wechat_mp_login(
    payload: WechatMpLoginRequest,
    service: ServiceDep,
) -> ApiResponse:
    """微信小程序登录（仅门户）。"""
    return success(await service.login_wechat_mp(AccountType.PORTAL, payload.code))


@portal_router.get(
    "/v1/portal/oauth/bindings",
    response_model=ApiResponse[list[OauthBindingResult]],
)
async def portal_oauth_bindings(
    service: ServiceDep,
    session: SessionDep,
) -> ApiResponse[list[OauthBindingResult]]:
    """列出当前门户账号三方绑定。"""
    return success(await service.list_current_bindings(session.account_id))


@portal_router.post(
    "/v1/portal/oauth/{provider}/bind/authorize",
    response_model=ApiResponse[OauthAuthorizeResult],
)
async def portal_oauth_bind_authorize(
    provider: str,
    service: ServiceDep,
    session: SessionDep,
) -> ApiResponse[OauthAuthorizeResult]:
    """发起门户三方绑定授权。"""
    result = await service.bind_authorize(
        AccountType.PORTAL, provider, session
    )
    return success(OauthAuthorizeResult(**result))


@portal_router.post(
    "/v1/portal/oauth/{provider}/unbind",
    response_model=ApiResponse[None],
)
async def portal_oauth_unbind(
    provider: str,
    service: ServiceDep,
    session: SessionDep,
) -> ApiResponse[None]:
    """解绑当前门户账号指定提供商。"""
    await service.unbind(session.account_id, provider)
    return success()
