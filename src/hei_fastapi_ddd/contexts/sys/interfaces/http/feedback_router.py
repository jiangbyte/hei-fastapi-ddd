""" Author: Charlie

由 HEI 代码生成器生成。
Author: jiangbyte

反馈路由：管理端 CRUD、提交与「我的反馈」接口，及门户端提交与查询接口。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.deps.auth import get_current_session, require_account_type, require_permission
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.sys.interfaces.http.feedback_schemas import (
    MyFeedbackPageQuery,
    SysFeedbackAdminPageQuery,
    SysFeedbackCreateRequest,
    SysFeedbackSchema,
    SysFeedbackUpdateRequest,
)
from hei_fastapi_ddd.contexts.sys.application.feedback.feedback_application_service import SysFeedbackService

admin_router = APIRouter()
portal_router = APIRouter()


# ==================== 管理端 CRUD ====================


@admin_router.get(
    "/v1/admin/sys/feedbacks/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:feedback:page")),
    ],
    response_model=ApiResponse[PageData[SysFeedbackSchema]],
)
async def page(
    query: Annotated[SysFeedbackAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysFeedbackSchema]]:
    """管理端分页查询反馈列表。"""
    return success(await SysFeedbackService(db).page_admin(query))


@admin_router.get(
    "/v1/admin/sys/feedbacks/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:feedback:detail")),
    ],
    response_model=ApiResponse[SysFeedbackSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysFeedbackSchema]:
    """管理端查询反馈详情。"""
    return success(await SysFeedbackService(db).detail(query))


@admin_router.post(
    "/v1/admin/sys/feedbacks/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:feedback:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: SysFeedbackUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    """管理端更新反馈状态与回复。"""
    await SysFeedbackService(db).update(payload, session)
    return success()


@admin_router.post(
    "/v1/admin/sys/feedbacks/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:feedback:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """管理端批量删除反馈。"""
    await SysFeedbackService(db).delete(payload)
    return success()


# ==================== 当前用户「我的反馈」（admin / portal） ====================


@admin_router.post(
    "/v1/admin/sys/feedbacks/submit",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[None],
)
async def admin_submit(
    payload: SysFeedbackCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    """管理端提交反馈。"""
    await SysFeedbackService(db).submit(payload, session)
    return success()


@admin_router.get(
    "/v1/admin/sys/feedbacks/my-page",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[PageData[SysFeedbackSchema]],
)
async def admin_my_page(
    query: Annotated[MyFeedbackPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[SysFeedbackSchema]]:
    """管理端分页查询当前用户的反馈。"""
    return success(await SysFeedbackService(db).page_my(query, session))


@admin_router.get(
    "/v1/admin/sys/feedbacks/my-detail",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[SysFeedbackSchema],
)
async def admin_my_detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysFeedbackSchema]:
    """管理端查询当前用户反馈详情。"""
    return success(await SysFeedbackService(db).detail_my(query, session))


@portal_router.post(
    "/v1/portal/sys/feedbacks/submit",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[None],
)
async def submit(
    payload: SysFeedbackCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    """门户端提交反馈。"""
    await SysFeedbackService(db).submit(payload, session)
    return success()


@portal_router.get(
    "/v1/portal/sys/feedbacks/my-page",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[PageData[SysFeedbackSchema]],
)
async def my_page(
    query: Annotated[MyFeedbackPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[SysFeedbackSchema]]:
    """门户端分页查询当前用户的反馈。"""
    return success(await SysFeedbackService(db).page_my(query, session))


@portal_router.get(
    "/v1/portal/sys/feedbacks/my-detail",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[SysFeedbackSchema],
)
async def my_detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysFeedbackSchema]:
    """门户端查询当前用户反馈详情。"""
    return success(await SysFeedbackService(db).detail_my(query, session))
