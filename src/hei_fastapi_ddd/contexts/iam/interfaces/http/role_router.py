""" Author: Charlie

角色管理 HTTP 路由：角色 CRUD 与用户/资源授权接口。
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
from hei_fastapi_ddd.contexts.iam.interfaces.http.role_schemas import (
    RoleAdminPageQuery,
    RoleCreateRequest,
    RoleGrantClientResourceRequest,
    RoleGrantResourceRequest,
    RoleGrantUserRequest,
    RoleOwnClientResourceQuery,
    RoleOwnClientResourceResponse,
    RoleOwnResourceQuery,
    RoleOwnResourceResponse,
    RoleOwnUserResponse,
    RoleUpdateRequest,
    SysRoleSchema,
)
from hei_fastapi_ddd.contexts.iam.application.role.role_application_service import RoleService

router = APIRouter()


@router.post(
    "/v1/admin/sys/roles/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:role:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: RoleCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await RoleService(db).create(payload, session)
    return success()


@router.post(
    "/v1/admin/sys/roles/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:role:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: RoleUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await RoleService(db).update(payload, session)
    return success()


@router.post(
    "/v1/admin/sys/roles/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:role:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await RoleService(db).delete(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/roles/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:role:detail")),
    ],
    response_model=ApiResponse[SysRoleSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysRoleSchema]:
    return success(await RoleService(db).detail(query, session))


@router.get(
    "/v1/admin/sys/roles/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:role:page")),
    ],
    response_model=ApiResponse[PageData[SysRoleSchema]],
)
async def page(
    query: Annotated[RoleAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[SysRoleSchema]]:
    return success(await RoleService(db).page_admin(query, session))


@router.get(
    "/v1/admin/sys/roles/own-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:role:ownresource")),
    ],
    response_model=ApiResponse[RoleOwnResourceResponse],
    summary="获取角色拥有资源",
)
async def own_resource(
    query: Annotated[RoleOwnResourceQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[RoleOwnResourceResponse]:
    return success(await RoleService(db).own_resource(query, session))


@router.post(
    "/v1/admin/sys/roles/grant-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:role:grantresource")),
    ],
    response_model=ApiResponse[None],
    summary="给角色授权资源",
)
async def grant_resource(
    payload: RoleGrantResourceRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await RoleService(db).grant_resource(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/roles/own-client-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:role:ownclientresource")),
    ],
    response_model=ApiResponse[RoleOwnClientResourceResponse],
    summary="获取角色拥有客户端资源",
)
async def own_client_resource(
    query: Annotated[RoleOwnClientResourceQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[RoleOwnClientResourceResponse]:
    return success(await RoleService(db).own_client_resource(query, session))


@router.post(
    "/v1/admin/sys/roles/grant-client-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:role:grantclientresource")),
    ],
    response_model=ApiResponse[None],
    summary="给角色授权客户端资源",
)
async def grant_client_resource(
    payload: RoleGrantClientResourceRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await RoleService(db).grant_client_resource(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/roles/own-user",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:role:ownuser")),
    ],
    response_model=ApiResponse[RoleOwnUserResponse],
    summary="获取角色拥有用户",
)
async def own_user(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[RoleOwnUserResponse]:
    return success(await RoleService(db).own_user(query, session))


@router.post(
    "/v1/admin/sys/roles/grant-user",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:role:grantuser")),
    ],
    response_model=ApiResponse[None],
    summary="给角色授权用户",
)
async def grant_user(
    payload: RoleGrantUserRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await RoleService(db).grant_user(payload, session)
    return success()
