"""Author: Charlie

实名认证路由：管理端用户、门户用户、管理端审核与快照管理。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.schema.base import IdQuery
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.deps.auth import get_current_session, require_account_type, require_permission
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.profile.interfaces.http.identity_schemas import (
    IdentityPageQuery,
    IdentityPageResponse,
    IdentityRevokeRequest,
    IdentityStatusResponse,
    RealNameCaseApproveRequest,
    RealNameCaseCallbackRequest,
    RealNameCaseDetailResponse,
    RealNameCaseInitResponse,
    RealNameCaseInitThirdPartyRequest,
    RealNameCaseMyPageQuery,
    RealNameCaseOptionsResponse,
    RealNameCaseRejectRequest,
    RealNameCaseReviewPageQuery,
    RealNameCaseSubmitRequest,
    RealNameCaseSummaryResponse,
)
from hei_fastapi_ddd.contexts.profile.application.identity.identity_application_service import ProfileIdentityService, RealNameCaseService

admin_user_router = APIRouter()
portal_user_router = APIRouter()
admin_manage_router = APIRouter()


# ==================== 管理端用户 ====================


@admin_user_router.get(
    "/v1/admin/profile/identity/status",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[IdentityStatusResponse],
)
async def admin_identity_status(
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[IdentityStatusResponse]:
    """查询当前管理端账户实名认证状态。"""
    return success(
        await ProfileIdentityService(db).get_user_status_for_account(session.account_id)
    )


@admin_user_router.get(
    "/v1/admin/real-name/case/options",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[RealNameCaseOptionsResponse],
)
async def admin_real_name_options(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[RealNameCaseOptionsResponse]:
    """查询实名认证可选项。"""
    return success(await RealNameCaseService(db).options())


@admin_user_router.post(
    "/v1/admin/real-name/case/submit",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[None],
)
async def admin_real_name_submit(
    payload: RealNameCaseSubmitRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """提交实名认证工单（人工通道）。"""
    await RealNameCaseService(db).submit(payload, session)
    return success()


@admin_user_router.post(
    "/v1/admin/real-name/case/init-third-party",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[RealNameCaseInitResponse],
)
async def admin_real_name_init_third_party(
    payload: RealNameCaseInitThirdPartyRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[RealNameCaseInitResponse]:
    """发起第三方实人认证。"""
    return success(await RealNameCaseService(db).init_third_party(payload, session))


@admin_user_router.post(
    "/v1/admin/real-name/case/callback",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[None],
)
async def admin_real_name_callback(
    payload: RealNameCaseCallbackRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """第三方实人认证回调。"""
    await RealNameCaseService(db).callback(payload)
    return success()


@admin_user_router.get(
    "/v1/admin/real-name/case/my-page",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[PageData[RealNameCaseSummaryResponse]],
)
async def admin_real_name_my_page(
    query: Annotated[RealNameCaseMyPageQuery, Depends()],
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[RealNameCaseSummaryResponse]]:
    """分页查询当前管理端账户的实名认证工单。"""
    return success(await RealNameCaseService(db).my_page(query, session))


# ==================== 门户用户 ====================


@portal_user_router.get(
    "/v1/portal/profile/identity/status",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[IdentityStatusResponse],
)
async def portal_identity_status(
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[IdentityStatusResponse]:
    """查询当前门户账户实名认证状态。"""
    return success(
        await ProfileIdentityService(db).get_user_status_for_account(session.account_id)
    )


@portal_user_router.get(
    "/v1/portal/real-name/case/options",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[RealNameCaseOptionsResponse],
)
async def portal_real_name_options(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[RealNameCaseOptionsResponse]:
    """查询实名认证可选项。"""
    return success(await RealNameCaseService(db).options())


@portal_user_router.post(
    "/v1/portal/real-name/case/submit",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[None],
)
async def portal_real_name_submit(
    payload: RealNameCaseSubmitRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """提交实名认证工单（人工通道）。"""
    await RealNameCaseService(db).submit(payload, session)
    return success()


@portal_user_router.post(
    "/v1/portal/real-name/case/init-third-party",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[RealNameCaseInitResponse],
)
async def portal_real_name_init_third_party(
    payload: RealNameCaseInitThirdPartyRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[RealNameCaseInitResponse]:
    """发起第三方实人认证。"""
    return success(await RealNameCaseService(db).init_third_party(payload, session))


@portal_user_router.post(
    "/v1/portal/real-name/case/callback",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[None],
)
async def portal_real_name_callback(
    payload: RealNameCaseCallbackRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """第三方实人认证回调。"""
    await RealNameCaseService(db).callback(payload)
    return success()


@portal_user_router.get(
    "/v1/portal/real-name/case/my-page",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[PageData[RealNameCaseSummaryResponse]],
)
async def portal_real_name_my_page(
    query: Annotated[RealNameCaseMyPageQuery, Depends()],
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[RealNameCaseSummaryResponse]]:
    """分页查询当前门户账户的实名认证工单。"""
    return success(await RealNameCaseService(db).my_page(query, session))


# ==================== 管理端审核与快照管理 ====================


@admin_manage_router.get(
    "/v1/admin/sys/real-name-case/review-page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:realname:verify")),
    ],
    response_model=ApiResponse[PageData[RealNameCaseSummaryResponse]],
)
async def real_name_review_page(
    query: Annotated[RealNameCaseReviewPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[RealNameCaseSummaryResponse]]:
    """管理端分页查询待审实名认证工单。"""
    return success(await RealNameCaseService(db).review_page(query))


@admin_manage_router.get(
    "/v1/admin/sys/real-name-case/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:realname:verify")),
    ],
    response_model=ApiResponse[RealNameCaseDetailResponse],
)
async def real_name_detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[RealNameCaseDetailResponse]:
    """管理端查询实名认证工单详情。"""
    return success(await RealNameCaseService(db).detail(query.id))


@admin_manage_router.post(
    "/v1/admin/sys/real-name-case/approve",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:realname:verify")),
    ],
    response_model=ApiResponse[None],
)
async def real_name_approve(
    payload: RealNameCaseApproveRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """管理端通过实名认证工单。"""
    await RealNameCaseService(db).approve(payload, session)
    return success()


@admin_manage_router.post(
    "/v1/admin/sys/real-name-case/reject",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:realname:verify")),
    ],
    response_model=ApiResponse[None],
)
async def real_name_reject(
    payload: RealNameCaseRejectRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """管理端驳回实名认证工单。"""
    await RealNameCaseService(db).reject(payload, session)
    return success()


@admin_manage_router.get(
    "/v1/admin/sys/identity/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:realnameidentity:revoke")),
    ],
    response_model=ApiResponse[PageData[IdentityPageResponse]],
)
async def identity_page(
    query: Annotated[IdentityPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[IdentityPageResponse]]:
    """管理端分页查询已认证实名快照。"""
    return success(await ProfileIdentityService(db).page(query))


@admin_manage_router.post(
    "/v1/admin/sys/identity/revoke",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:realnameidentity:revoke")),
    ],
    response_model=ApiResponse[None],
)
async def identity_revoke(
    payload: IdentityRevokeRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """管理端撤销账号实名认证。"""
    await ProfileIdentityService(db).revoke(payload, session.account_id)
    return success()
