"""代码生成管理端接口。"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response

from hei_fastapi_ddd.contexts.sys.api.codegen_schemas import (
    CodegenFieldsQuery,
    CodegenFieldsUpdateBatchRequest,
    CodegenParentResourceOption,
    CodegenParentResourcesQuery,
    CodegenPlanCreateRequest,
    CodegenPlanPageQuery,
    CodegenPlanUpdateRequest,
    CodegenPreviewFile as CodegenPreviewFileSchema,
    CodegenPreviewSchema,
    CodegenTableColumnsQuery,
    DatabaseColumnSchema,
    DatabaseTableSchema,
    SysCodegenFieldSchema,
    SysCodegenPlanSchema,
)
from hei_fastapi_ddd.contexts.sys.application.codegen.codegen_application_service import (
    CodegenService,
)
from hei_fastapi_ddd.contexts.sys.application.codegen.dto import (
    CodegenFieldsQuery as CodegenFieldsQueryDto,
    CodegenFieldsUpdateBatchCommand,
    CodegenIdQuery,
    CodegenIdsCommand,
    CodegenParentResourcesQuery as CodegenParentResourcesQueryDto,
    CodegenPlanCreateCommand,
    CodegenPlanPageQuery as CodegenPlanPageQueryDto,
    CodegenPlanUpdateCommand,
    CodegenTableColumnsQuery as CodegenTableColumnsQueryDto,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.wiring import get_codegen_service
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import require_account_type, require_permission
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


def _map_plan_page(page: PageData[dict]) -> PageData[SysCodegenPlanSchema]:
    return PageData(
        current=page.current,
        size=page.size,
        total=page.total,
        records=[SysCodegenPlanSchema.model_validate(r) for r in page.records],
    )


def _map_resource_options(items: list[dict[str, Any]]) -> list[CodegenParentResourceOption]:
    def build(node: dict[str, Any]) -> CodegenParentResourceOption:
        children = node.get("children")
        return CodegenParentResourceOption(
            id=node["id"],
            parent_id=node.get("parent_id"),
            name=node["name"],
            resource_type=node["resource_type"],
            module_id=node.get("module_id"),
            sort=node.get("sort"),
            weight=node.get("weight"),
            children=[build(c) for c in children] if children else None,
        )

    return [build(item) for item in items]


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
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> ApiResponse[None]:
    await service.create(CodegenPlanCreateCommand.model_validate(payload.model_dump()))
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
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> ApiResponse[None]:
    await service.update(CodegenPlanUpdateCommand.model_validate(payload.model_dump()))
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
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> ApiResponse[None]:
    await service.delete(CodegenIdsCommand(ids=payload.ids))
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
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> ApiResponse[SysCodegenPlanSchema]:
    return success(
        SysCodegenPlanSchema.model_validate(
            await service.detail(CodegenIdQuery(id=query.id))
        )
    )


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
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> ApiResponse[PageData[SysCodegenPlanSchema]]:
    return success(
        _map_plan_page(
            await service.page_admin(
                CodegenPlanPageQueryDto.model_validate(query.model_dump())
            )
        )
    )


@router.get(
    "/v1/admin/sys/codegen/tables",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:tables")),
    ],
    response_model=ApiResponse[list[DatabaseTableSchema]],
)
async def tables(
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> ApiResponse[list[DatabaseTableSchema]]:
    rows = await service.tables()
    return success([DatabaseTableSchema.model_validate(r) for r in rows])


@router.get(
    "/v1/admin/sys/codegen/table-columns",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:tables")),
    ],
    response_model=ApiResponse[list[DatabaseColumnSchema]],
)
async def table_columns(
    query: Annotated[CodegenTableColumnsQuery, Depends()],
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> ApiResponse[list[DatabaseColumnSchema]]:
    rows = await service.table_columns(
        CodegenTableColumnsQueryDto.model_validate(query.model_dump())
    )
    return success([DatabaseColumnSchema.model_validate(r) for r in rows])


@router.get(
    "/v1/admin/sys/codegen/fields",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:detail")),
    ],
    response_model=ApiResponse[list[SysCodegenFieldSchema]],
)
async def fields(
    query: Annotated[CodegenFieldsQuery, Depends()],
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> ApiResponse[list[SysCodegenFieldSchema]]:
    rows = await service.fields(
        CodegenFieldsQueryDto.model_validate(query.model_dump())
    )
    return success([SysCodegenFieldSchema.model_validate(r) for r in rows])


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
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> ApiResponse[None]:
    await service.update_fields_batch(
        CodegenFieldsUpdateBatchCommand.model_validate(payload.model_dump())
    )
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
    query: Annotated[CodegenParentResourcesQuery, Depends()],
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> ApiResponse[list[CodegenParentResourceOption]]:
    rows = await service.parent_resources(
        CodegenParentResourcesQueryDto.model_validate(query.model_dump())
    )
    return success(_map_resource_options(rows))


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
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> ApiResponse[CodegenPreviewSchema]:
    data = await service.preview(CodegenIdQuery(id=query.id))
    files = [
        CodegenPreviewFileSchema(
            path=f.path,
            language=f.language,
            content=f.content,
        )
        for f in data["files"]
    ]
    return success(CodegenPreviewSchema(files=files))


@router.get(
    "/v1/admin/sys/codegen/download",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:codegen:download")),
    ],
)
async def download(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[CodegenService, Depends(get_codegen_service)],
) -> Response:
    content, filename = await service.download(CodegenIdQuery(id=query.id))
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
