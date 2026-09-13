""" Author: Charlie

账户管理 HTTP 路由：账户 CRUD 与角色/组/部门/资源授权接口。
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
from hei_fastapi_ddd.contexts.iam.interfaces.http.account_schemas import (
    AccountAdminPageQuery,
    AccountCreateRequest,
    AccountGrantClientResourceRequest,
    AccountGrantDeptRequest,
    AccountGrantGroupRequest,
    AccountGrantResourceRequest,
    AccountGrantRoleRequest,
    AccountOwnClientResourceResponse,
    AccountOwnDeptResponse,
    AccountOwnGroupResponse,
    AccountOwnResourceResponse,
    AccountOwnRoleResponse,
    AccountUpdateLoginIdentityRequest,
    AccountUpdateRequest,
    SysAccountListSchema,
    SysAccountSchema,
)
from hei_fastapi_ddd.contexts.iam.application.account.account_application_service import AccountService

router = APIRouter()


@router.post(
    "/v1/admin/sys/accounts/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: AccountCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await AccountService(db).create(payload)
    return success()


@router.post(
    "/v1/admin/sys/accounts/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: AccountUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await AccountService(db).update(payload, session)
    return success()


@router.post(
    "/v1/admin/sys/accounts/update-login-identity",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:update")),
    ],
    response_model=ApiResponse[None],
)
async def update_login_identity(
    payload: AccountUpdateLoginIdentityRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await AccountService(db).update_login_identity(payload, session)
    return success()


@router.post(
    "/v1/admin/sys/accounts/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await AccountService(db).delete(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/accounts/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:detail")),
    ],
    response_model=ApiResponse[SysAccountSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysAccountSchema]:
    return success(await AccountService(db).detail(query, session))


@router.get(
    "/v1/admin/sys/accounts/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:page")),
    ],
    response_model=ApiResponse[PageData[SysAccountListSchema]],
)
async def page(
    query: Annotated[AccountAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[SysAccountListSchema]]:
    return success(await AccountService(db).page_admin(query, session))


@router.get(
    "/v1/admin/sys/accounts/own-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:ownresource")),
    ],
    response_model=ApiResponse[AccountOwnResourceResponse],
    summary="获取用户资源授权",
)
async def own_resource(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[AccountOwnResourceResponse]:
    return success(await AccountService(db).own_resource(query, session))


@router.post(
    "/v1/admin/sys/accounts/grant-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:grantresource")),
    ],
    response_model=ApiResponse[None],
    summary="给用户授权资源",
)
async def grant_resource(
    payload: AccountGrantResourceRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await AccountService(db).grant_resource(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/accounts/own-client-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:ownclientresource")),
    ],
    response_model=ApiResponse[AccountOwnClientResourceResponse],
    summary="获取用户客户端资源授权",
)
async def own_client_resource(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[AccountOwnClientResourceResponse]:
    return success(await AccountService(db).own_client_resource(query, session))


@router.post(
    "/v1/admin/sys/accounts/grant-client-resource",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:grantclientresource")),
    ],
    response_model=ApiResponse[None],
    summary="给用户授权客户端资源",
)
async def grant_client_resource(
    payload: AccountGrantClientResourceRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await AccountService(db).grant_client_resource(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/accounts/own-role",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:ownrole")),
    ],
    response_model=ApiResponse[AccountOwnRoleResponse],
    summary="获取用户角色授权",
)
async def own_role(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[AccountOwnRoleResponse]:
    return success(await AccountService(db).own_role(query, session))


@router.post(
    "/v1/admin/sys/accounts/grant-role",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:grantrole")),
    ],
    response_model=ApiResponse[None],
    summary="给用户授权角色",
)
async def grant_role(
    payload: AccountGrantRoleRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await AccountService(db).grant_role(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/accounts/own-group",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:owngroup")),
    ],
    response_model=ApiResponse[AccountOwnGroupResponse],
    summary="获取用户组授权",
)
async def own_group(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[AccountOwnGroupResponse]:
    return success(await AccountService(db).own_group(query, session))


@router.post(
    "/v1/admin/sys/accounts/grant-group",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:grantgroup")),
    ],
    response_model=ApiResponse[None],
    summary="给用户授权用户组",
)
async def grant_group(
    payload: AccountGrantGroupRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await AccountService(db).grant_group(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/accounts/own-dept",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:owndept")),
    ],
    response_model=ApiResponse[AccountOwnDeptResponse],
    summary="获取用户部门授权",
)
async def own_dept(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[AccountOwnDeptResponse]:
    return success(await AccountService(db).own_dept(query, session))


@router.post(
    "/v1/admin/sys/accounts/grant-dept",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:account:grantdept")),
    ],
    response_model=ApiResponse[None],
    summary="给用户授权部门",
)
async def grant_dept(
    payload: AccountGrantDeptRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await AccountService(db).grant_dept(payload, session)
    return success()
