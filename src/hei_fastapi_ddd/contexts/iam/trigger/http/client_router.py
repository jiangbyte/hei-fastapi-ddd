""" Author: Charlie

客户端模块与客户端资源管理 HTTP 路由。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.api.client_schemas import (
    ClientModuleAdminPageQuery,
    ClientModuleCreateRequest,
    ClientModuleSelectorQuery,
    ClientModuleUpdateRequest,
    ClientResourceAdminPageQuery,
    ClientResourceCreateRequest,
    ClientResourcePermissionBindRequest,
    ClientResourceTreeNode,
    ClientResourceTreeQuery,
    ClientResourceUpdateRequest,
    SysClientModuleSchema,
    SysClientResourcePermissionRelSchema,
    SysClientResourceSchema,
)
from hei_fastapi_ddd.contexts.iam.application.client.client_application_service import (
    ClientModuleService,
    ClientResourceService,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.wiring import (
    get_client_module_service,
    get_client_resource_service,
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
    "/v1/admin/sys/client-modules/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientmodule:create")),
    ],
    response_model=ApiResponse[None],
)
async def create_client_module(
    payload: ClientModuleCreateRequest,
    service: Annotated[ClientResourceService, Depends(get_client_resource_service)],
) -> ApiResponse[None]:
    await module_service.create(payload.model_dump())
    return success()


@router.post(
    "/v1/admin/sys/client-modules/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientmodule:update")),
    ],
    response_model=ApiResponse[None],
)
async def update_client_module(
    payload: ClientModuleUpdateRequest,
    service: Annotated[ClientResourceService, Depends(get_client_resource_service)],
) -> ApiResponse[None]:
    await module_service.update(payload.model_dump())
    return success()


@router.post(
    "/v1/admin/sys/client-modules/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientmodule:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete_client_module(
    payload: IdsRequest,
    service: Annotated[ClientResourceService, Depends(get_client_resource_service)],
) -> ApiResponse[None]:
    await module_service.delete(payload)
    return success()


@router.get(
    "/v1/admin/sys/client-modules/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientmodule:detail")),
    ],
    response_model=ApiResponse[SysClientModuleSchema],
)
async def client_module_detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysClientModuleSchema]:
    return success(await module_service.detail(query))


@router.get(
    "/v1/admin/sys/client-modules/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientmodule:page")),
    ],
    response_model=ApiResponse[PageData[SysClientModuleSchema]],
)
async def client_module_page(
    query: Annotated[ClientModuleAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysClientModuleSchema]]:
    return success(await module_service.page_admin(query.model_dump()))


@router.get(
    "/v1/admin/sys/client-modules/selector",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientmodule:page")),
    ],
    response_model=ApiResponse[list[SysClientModuleSchema]],
)
async def client_module_selector(
    query: Annotated[ClientModuleSelectorQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[SysClientModuleSchema]]:
    return success(await module_service.selector(query))


@router.post(
    "/v1/admin/sys/client-resources/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientresource:create")),
    ],
    response_model=ApiResponse[None],
)
async def create_client_resource(
    payload: ClientResourceCreateRequest,
    service: Annotated[ClientResourceService, Depends(get_client_resource_service)],
) -> ApiResponse[None]:
    await service.create(payload.model_dump())
    return success()


@router.post(
    "/v1/admin/sys/client-resources/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientresource:update")),
    ],
    response_model=ApiResponse[None],
)
async def update_client_resource(
    payload: ClientResourceUpdateRequest,
    service: Annotated[ClientResourceService, Depends(get_client_resource_service)],
) -> ApiResponse[None]:
    await service.update(payload.model_dump())
    return success()


@router.post(
    "/v1/admin/sys/client-resources/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientresource:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete_client_resource(
    payload: IdsRequest,
    service: Annotated[ClientResourceService, Depends(get_client_resource_service)],
) -> ApiResponse[None]:
    await service.delete(payload)
    return success()


@router.get(
    "/v1/admin/sys/client-resources/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientresource:detail")),
    ],
    response_model=ApiResponse[SysClientResourceSchema],
)
async def client_resource_detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysClientResourceSchema]:
    return success(await service.detail(query))


@router.get(
    "/v1/admin/sys/client-resources/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientresource:page")),
    ],
    response_model=ApiResponse[PageData[SysClientResourceSchema]],
)
async def client_resource_page(
    query: Annotated[ClientResourceAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysClientResourceSchema]]:
    return success(await service.page_admin(query.model_dump()))


@router.get(
    "/v1/admin/sys/client-resources/tree",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientresource:list")),
    ],
    response_model=ApiResponse[list[ClientResourceTreeNode]],
)
async def client_resource_tree(
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[ClientResourceTreeQuery, Depends()],
) -> ApiResponse[list[ClientResourceTreeNode]]:
    return success(await service.list_tree(session, query.model_dump()))


@router.post(
    "/v1/admin/client-resource-permissions",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:clientresource:grant")),
    ],
    response_model=ApiResponse[SysClientResourcePermissionRelSchema],
)
async def bind_client_resource_permission(
    payload: ClientResourcePermissionBindRequest,
    service: Annotated[ClientResourceService, Depends(get_client_resource_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysClientResourcePermissionRelSchema]:
    return success(await service.bind_permission(payload.model_dump(), session))
