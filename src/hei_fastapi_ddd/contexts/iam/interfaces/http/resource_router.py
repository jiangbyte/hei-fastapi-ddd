""" Author: Charlie

资源管理 HTTP 路由：资源树、资源模块、按钮与资源权限相关接口。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import (
    ResourceModuleService,
    ResourceService,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.iam_schemas import PermissionRegistryItem
from hei_fastapi_ddd.contexts.iam.interfaces.http.resource_schemas import (
    ResourceAdminPageQuery,
    ResourceButtonCreateRequest,
    ResourceButtonPageQuery,
    ResourceButtonSchema,
    ResourceButtonUpdateRequest,
    ResourceCreateRequest,
    ResourceModuleAdminPageQuery,
    ResourceModuleCreateRequest,
    ResourceModuleUpdateRequest,
    ResourcePermissionBindRequest,
    ResourceTreeNode,
    ResourceTreeQuery,
    ResourceUpdateRequest,
    SysResourceModuleSchema,
    SysResourceSchema,
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
    "/v1/admin/sys/resources/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: ResourceCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await ResourceService(db).create(payload)
    return success()


@router.post(
    "/v1/admin/sys/resources/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: ResourceUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await ResourceService(db).update(payload)
    return success()


@router.post(
    "/v1/admin/sys/resources/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await ResourceService(db).delete(payload)
    return success()


@router.get(
    "/v1/admin/sys/resources/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:detail")),
    ],
    response_model=ApiResponse[SysResourceSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysResourceSchema]:
    return success(await ResourceService(db).detail(query))


@router.get(
    "/v1/admin/sys/resources/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:page")),
    ],
    response_model=ApiResponse[PageData[SysResourceSchema]],
)
async def page(
    query: Annotated[ResourceAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysResourceSchema]]:
    return success(await ResourceService(db).page_admin(query))


@router.get(
    "/v1/admin/sys/resources/current",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
    ],
    response_model=ApiResponse[list[SysResourceSchema]],
)
async def current_resources(
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[SysResourceSchema]]:
    return success(
        await ResourceService(db).list_current_resources(
            session,
            module_client=AccountType.ADMIN,
        )
    )


@router.get(
    "/v1/admin/sys/resources/tree",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:list")),
    ],
    response_model=ApiResponse[list[ResourceTreeNode]],
)
async def list_resource_tree(
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[ResourceTreeQuery, Depends()],
) -> ApiResponse[list[ResourceTreeNode]]:
    return success(await ResourceService(db).list_resource_tree(session, query))


@router.post(
    "/v1/admin/resource-permissions",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:grant")),
    ],
    response_model=ApiResponse[None],
)
async def bind_resource_permission(
    payload: ResourcePermissionBindRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await ResourceService(db).bind_resource_permission(payload, session)
    return success()


@router.get(
    "/v1/admin/permission-registry",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:grant")),
    ],
    response_model=ApiResponse[list[PermissionRegistryItem]],
)
async def permission_registry(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[PermissionRegistryItem]]:
    return success(await ResourceService(db).list_permission_registry_items())


@router.post(
    "/v1/admin/sys/resource-buttons/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:create")),
    ],
    response_model=ApiResponse[None],
)
async def create_button(
    payload: ResourceButtonCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await ResourceService(db).create_button(payload, session)
    return success()


@router.post(
    "/v1/admin/sys/resource-buttons/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:update")),
    ],
    response_model=ApiResponse[None],
)
async def update_button(
    payload: ResourceButtonUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await ResourceService(db).update_button(payload, session)
    return success()


@router.post(
    "/v1/admin/sys/resource-buttons/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete_button(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await ResourceService(db).delete_button(payload)
    return success()


@router.get(
    "/v1/admin/sys/resource-buttons/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resource:list")),
    ],
    response_model=ApiResponse[PageData[ResourceButtonSchema]],
)
async def button_page(
    query: Annotated[ResourceButtonPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[ResourceButtonSchema]]:
    return success(await ResourceService(db).page_buttons(query))


@router.post(
    "/v1/admin/sys/resource-modules/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resourcemodule:create")),
    ],
    response_model=ApiResponse[None],
)
async def create_resource_module(
    payload: ResourceModuleCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await ResourceModuleService(db).create(payload)
    return success()


@router.post(
    "/v1/admin/sys/resource-modules/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resourcemodule:update")),
    ],
    response_model=ApiResponse[None],
)
async def update_resource_module(
    payload: ResourceModuleUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await ResourceModuleService(db).update(payload)
    return success()


@router.post(
    "/v1/admin/sys/resource-modules/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resourcemodule:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete_resource_module(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await ResourceModuleService(db).delete(payload)
    return success()


@router.get(
    "/v1/admin/sys/resource-modules/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resourcemodule:detail")),
    ],
    response_model=ApiResponse[SysResourceModuleSchema],
)
async def resource_module_detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysResourceModuleSchema]:
    return success(await ResourceModuleService(db).detail(query))


@router.get(
    "/v1/admin/sys/resource-modules/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resourcemodule:page")),
    ],
    response_model=ApiResponse[PageData[SysResourceModuleSchema]],
)
async def resource_module_page(
    query: Annotated[ResourceModuleAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysResourceModuleSchema]]:
    return success(await ResourceModuleService(db).page_admin(query))


@router.get(
    "/v1/admin/sys/resource-modules/selector",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:resourcemodule:page")),
    ],
    response_model=ApiResponse[list[SysResourceModuleSchema]],
)
async def resource_module_selector(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[SysResourceModuleSchema]]:
    return success(await ResourceModuleService(db).selector())
