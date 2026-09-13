""" Author: Charlie

账户组管理 HTTP 路由：账户组 CRUD 与成员/角色/资源授权接口。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.group.group_application_service import GroupService
from hei_fastapi_ddd.contexts.iam.interfaces.http.group_schemas import (
    GroupAdminPageQuery,
    GroupCreateRequest,
    GroupGrantClientResourceRequest,
    GroupGrantResourceRequest,
    GroupGrantRoleRequest,
    GroupGrantUserRequest,
    GroupOwnClientResourceQuery,
    GroupOwnClientResourceResponse,
    GroupOwnResourceQuery,
    GroupOwnResourceResponse,
    GroupOwnRoleQuery,
    GroupOwnRoleResponse,
    GroupOwnUserResponse,
    GroupUpdateRequest,
    SysGroupSchema,
)
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_session,
    require_account_type,
    require_permission,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.post(
    "/v1/admin/sys/groups/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: GroupCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await GroupService(db).create(payload, session)
    return success()


@router.post(
    "/v1/admin/sys/groups/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: GroupUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await GroupService(db).update(payload, session)
    return success()


@router.post(
    "/v1/admin/sys/groups/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await GroupService(db).delete(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/groups/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:detail")),
    ],
    response_model=ApiResponse[SysGroupSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysGroupSchema]:
    return success(await GroupService(db).detail(query, session))


@router.get(
    "/v1/admin/sys/groups/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:page")),
    ],
    response_model=ApiResponse[PageData[SysGroupSchema]],
)
async def page(
    query: Annotated[GroupAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[SysGroupSchema]]:
    return success(await GroupService(db).page_admin(query, session))


@router.get(
    "/v1/admin/sys/groups/own-user",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:ownuser")),
    ],
    response_model=ApiResponse[GroupOwnUserResponse],
    summary="获取用户组成员授权",
)
async def own_user(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[GroupOwnUserResponse]:
    return success(await GroupService(db).own_user(query, session))


@router.post(
    "/v1/admin/sys/groups/grant-user",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:grantuser")),
    ],
    response_model=ApiResponse[None],
    summary="给用户组授权成员",
)
async def grant_user(
    payload: GroupGrantUserRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await GroupService(db).grant_user(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/groups/own-role",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:ownrole")),
    ],
    response_model=ApiResponse[GroupOwnRoleResponse],
    summary="获取用户组角色授权",
)
async def own_role(
    query: Annotated[GroupOwnRoleQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[GroupOwnRoleResponse]:
    return success(await GroupService(db).own_role(query, session))


@router.post(
    "/v1/admin/sys/groups/grant-role",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:grantrole")),
    ],
    response_model=ApiResponse[None],
    summary="给用户组授权角色",
)
async def grant_role(
    payload: GroupGrantRoleRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await GroupService(db).grant_role(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/groups/own-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:ownresource")),
    ],
    response_model=ApiResponse[GroupOwnResourceResponse],
    summary="获取用户组资源授权",
)
async def own_resource(
    query: Annotated[GroupOwnResourceQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[GroupOwnResourceResponse]:
    return success(await GroupService(db).own_resource(query, session))


@router.post(
    "/v1/admin/sys/groups/grant-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:grantresource")),
    ],
    response_model=ApiResponse[None],
    summary="给用户组授权资源",
)
async def grant_resource(
    payload: GroupGrantResourceRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await GroupService(db).grant_resource(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/groups/own-client-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:ownclientresource")),
    ],
    response_model=ApiResponse[GroupOwnClientResourceResponse],
    summary="获取用户组客户端资源授权",
)
async def own_client_resource(
    query: Annotated[GroupOwnClientResourceQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[GroupOwnClientResourceResponse]:
    return success(await GroupService(db).own_client_resource(query, session))


@router.post(
    "/v1/admin/sys/groups/grant-client-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:group:grantclientresource")),
    ],
    response_model=ApiResponse[None],
    summary="给用户组授权客户端资源",
)
async def grant_client_resource(
    payload: GroupGrantClientResourceRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await GroupService(db).grant_client_resource(payload, session)
    return success()
