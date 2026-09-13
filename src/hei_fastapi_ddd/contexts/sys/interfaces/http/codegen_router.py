""" Author: Charlie

代码生成管理端接口：方案的增删改查、数据库内省与预览下载。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.deps.auth import require_account_type, require_permission
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.sys.interfaces.http.codegen_schemas import (
    CodegenFieldsQuery,
    CodegenFieldsUpdateBatchRequest,
    CodegenParentResourceOption,
    CodegenParentResourcesQuery,
    CodegenPlanCreateRequest,
    CodegenPlanPageQuery,
    CodegenPlanUpdateRequest,
    CodegenPreviewSchema,
    CodegenTableColumnsQuery,
    DatabaseColumnSchema,
    DatabaseTableSchema,
    SysCodegenFieldSchema,
    SysCodegenPlanSchema,
)
from hei_fastapi_ddd.contexts.sys.application.codegen.codegen_application_service import CodegenService

router = APIRouter()


@router.post(
    "/v1/admin/sys/codegen/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: CodegenPlanCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """新增代码生成方案。"""
    await CodegenService(db).create(payload)
    return success()


@router.post(
    "/v1/admin/sys/codegen/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: CodegenPlanUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """更新代码生成方案。"""
    await CodegenService(db).update(payload)
    return success()


@router.post(
    "/v1/admin/sys/codegen/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """批量删除代码生成方案。"""
    await CodegenService(db).delete(payload)
    return success()


@router.get(
    "/v1/admin/sys/codegen/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:detail")),
    ],
    response_model=ApiResponse[SysCodegenPlanSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysCodegenPlanSchema]:
    """查询方案详情。"""
    return success(await CodegenService(db).detail(query))


@router.get(
    "/v1/admin/sys/codegen/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:page")),
    ],
    response_model=ApiResponse[PageData[SysCodegenPlanSchema]],
)
async def page(
    query: Annotated[CodegenPlanPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysCodegenPlanSchema]]:
    """分页查询方案。"""
    return success(await CodegenService(db).page_admin(query))


@router.get(
    "/v1/admin/sys/codegen/tables",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:tables")),
    ],
    response_model=ApiResponse[list[DatabaseTableSchema]],
)
async def tables(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[DatabaseTableSchema]]:
    """列出可生成的数据库表。"""
    return success(await CodegenService(db).tables())


@router.get(
    "/v1/admin/sys/codegen/table-columns",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:tables")),
    ],
    response_model=ApiResponse[list[DatabaseColumnSchema]],
)
async def table_columns(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[CodegenTableColumnsQuery, Depends()],
) -> ApiResponse[list[DatabaseColumnSchema]]:
    """查询指定表的列元数据。"""
    return success(await CodegenService(db).table_columns(query))


@router.get(
    "/v1/admin/sys/codegen/fields",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:detail")),
    ],
    response_model=ApiResponse[list[SysCodegenFieldSchema]],
)
async def fields(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[CodegenFieldsQuery, Depends()],
) -> ApiResponse[list[SysCodegenFieldSchema]]:
    """查询方案的字段配置。"""
    return success(await CodegenService(db).fields(query))


@router.post(
    "/v1/admin/sys/codegen/fields/update-batch",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:update")),
    ],
    response_model=ApiResponse[None],
)
async def update_fields_batch(
    payload: CodegenFieldsUpdateBatchRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """批量替换方案的字段配置。"""
    await CodegenService(db).update_fields_batch(payload)
    return success()


@router.get(
    "/v1/admin/sys/codegen/parent-resources",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:detail")),
    ],
    response_model=ApiResponse[list[CodegenParentResourceOption]],
)
async def parent_resources(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[CodegenParentResourcesQuery, Depends()],
) -> ApiResponse[list[CodegenParentResourceOption]]:
    """查询可作为父资源的资源选项。"""
    return success(await CodegenService(db).parent_resources(query))


@router.get(
    "/v1/admin/sys/codegen/preview",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:preview")),
    ],
    response_model=ApiResponse[CodegenPreviewSchema],
)
async def preview(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[CodegenPreviewSchema]:
    """渲染方案生成文件的预览。"""
    return success(await CodegenService(db).preview(query))


@router.get(
    "/v1/admin/sys/codegen/download",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:download")),
    ],
)
async def download(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    """将预览文件打包为 zip 下载。"""
    content, filename = await CodegenService(db).download(query)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
