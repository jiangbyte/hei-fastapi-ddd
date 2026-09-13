""" Author: Charlie

消息通知路由：管理端消息管理接口，及动态注册的当前用户消息接口。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType, account_type_url_segment
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.schema.wire import WireInt
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_session,
    get_optional_session,
    require_account_type,
    require_permission,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.sys.interfaces.http.notice_schemas import (
    MyNoticePageQuery,
    NoticeReadRequest,
    PinNoticeRequest,
    SysNoticeAdminPageQuery,
    SysNoticeCreateRequest,
    SysNoticeSchema,
    SysNoticeUpdateRequest,
)
from hei_fastapi_ddd.contexts.sys.application.notice.notice_application_service import SysNoticeService

admin_router = APIRouter()
portal_router = APIRouter()


@portal_router.get(
    "/v1/portal/sys/notices/list",
    response_model=ApiResponse[PageData[SysNoticeSchema]],
)
async def portal_notice_list(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[MyNoticePageQuery, Depends()],
    session: Annotated[SessionPayload | None, Depends(get_optional_session)] = None,
) -> ApiResponse[PageData[SysNoticeSchema]]:
    """门户端公告列表查询。"""
    return success(await SysNoticeService(db).page_portal_list(query, session))


@admin_router.post(
    "/v1/admin/sys/notices/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:notice:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: SysNoticeCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """管理端创建消息。"""
    await SysNoticeService(db).create(payload)
    return success()


@admin_router.post(
    "/v1/admin/sys/notices/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:notice:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: SysNoticeUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """管理端更新消息。"""
    await SysNoticeService(db).update(payload)
    return success()


@admin_router.post(
    "/v1/admin/sys/notices/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:notice:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """管理端批量删除消息。"""
    await SysNoticeService(db).delete(payload)
    return success()


@admin_router.get(
    "/v1/admin/sys/notices/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:notice:detail")),
    ],
    response_model=ApiResponse[SysNoticeSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysNoticeSchema]:
    """管理端查询消息详情。"""
    return success(await SysNoticeService(db).detail(query))


@admin_router.get(
    "/v1/admin/sys/notices/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:notice:page")),
    ],
    response_model=ApiResponse[PageData[SysNoticeSchema]],
)
async def page(
    query: Annotated[SysNoticeAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysNoticeSchema]]:
    """管理端分页查询消息。"""
    return success(await SysNoticeService(db).page_admin(query))


@admin_router.post(
    "/v1/admin/sys/notices/publish",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:notice:publish")),
    ],
    response_model=ApiResponse[None],
)
async def publish(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    """管理端发布消息。"""
    await SysNoticeService(db).publish(payload, session)
    return success()


@admin_router.post(
    "/v1/admin/sys/notices/revoke",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:notice:revoke")),
    ],
    response_model=ApiResponse[None],
)
async def revoke(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """管理端撤回消息。"""
    await SysNoticeService(db).revoke(payload)
    return success()


@admin_router.post(
    "/v1/admin/sys/notices/pin",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:notice:pin")),
    ],
    response_model=ApiResponse[None],
)
async def pin(
    payload: PinNoticeRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """管理端置顶/取消置顶公告。"""
    await SysNoticeService(db).pin(payload)
    return success()


def register_current_user_routes(router: APIRouter, account_type: AccountType) -> None:
    """为指定账户类型动态注册「我的消息」相关路由。"""
    # 与静态装饰器相同：字面量 /v1/ + 账户类型段（勿另造版本常量）。
    base = f"/v1/{account_type_url_segment(account_type)}/sys/notices"
    deps = [Depends(require_account_type(account_type))]

    @router.get(
        f"{base}/my-page",
        dependencies=deps,
        response_model=ApiResponse[PageData[SysNoticeSchema]],
    )
    async def my_page(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        session: Annotated[SessionPayload, Depends(get_current_session)],
        query: Annotated[MyNoticePageQuery, Depends()],
    ) -> ApiResponse[PageData[SysNoticeSchema]]:
        """当前用户分页查询可见消息。"""
        return success(await SysNoticeService(db).page_my(query, session))

    @router.get(
        f"{base}/my-detail",
        dependencies=deps,
        response_model=ApiResponse[SysNoticeSchema],
    )
    async def my_detail(
        query: Annotated[IdQuery, Depends()],
        db: Annotated[AsyncSession, Depends(get_db_session)],
        session: Annotated[SessionPayload, Depends(get_current_session)],
    ) -> ApiResponse[SysNoticeSchema]:
        """当前用户查询消息详情。"""
        return success(await SysNoticeService(db).my_detail(query, session))

    @router.get(
        f"{base}/unread-count",
        dependencies=deps,
        response_model=ApiResponse[WireInt],
    )
    async def unread_count(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        session: Annotated[SessionPayload, Depends(get_current_session)],
    ) -> ApiResponse[WireInt]:
        """当前用户未读消息数。"""
        return success(await SysNoticeService(db).count_unread(session))

    @router.post(
        f"{base}/read",
        dependencies=deps,
        response_model=ApiResponse[None],
    )
    async def read(
        payload: NoticeReadRequest,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        session: Annotated[SessionPayload, Depends(get_current_session)],
    ) -> ApiResponse[None]:
        """当前用户标记指定消息为已读。"""
        await SysNoticeService(db).mark_read(payload, session)
        return success()

    @router.post(
        f"{base}/read-all",
        dependencies=deps,
        response_model=ApiResponse[None],
    )
    async def read_all(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        session: Annotated[SessionPayload, Depends(get_current_session)],
    ) -> ApiResponse[None]:
        """当前用户标记全部消息为已读。"""
        await SysNoticeService(db).mark_all_read(session)
        return success()


register_current_user_routes(admin_router, AccountType.ADMIN)
register_current_user_routes(portal_router, AccountType.PORTAL)
