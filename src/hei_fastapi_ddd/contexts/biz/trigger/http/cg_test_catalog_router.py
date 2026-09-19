"""cg_test_catalog HTTP 适配：Schema ↔ Command，经 wiring 注入服务。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from hei_fastapi_ddd.contexts.biz.api.cg_test_catalog_schemas import (
    CgTestCatalogAdminPageQuery,
    CgTestCatalogCreateRequest,
    CgTestCatalogDetailSchema,
    CgTestCatalogSchema,
    CgTestCatalogTreeNode,
    CgTestCatalogUpdateRequest,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_catalog.cg_test_catalog_application_service import (
    CgTestCatalogService,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_catalog.dto import (
    CgTestCatalogCreateCommand,
    CgTestCatalogKeywordQuery,
    CgTestCatalogPageQuery,
    CgTestCatalogUpdateCommand,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.wiring import get_cg_test_catalog_service
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_session,
    require_account_type,
    require_permission,
)
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, KeywordQuery
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.post(
    "/v1/admin/biz/cg-test-catalog/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestcatalog:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: CgTestCatalogCreateRequest,
    service: Annotated[CgTestCatalogService, Depends(get_cg_test_catalog_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.create(
        CgTestCatalogCreateCommand.model_validate(payload.model_dump()),
        session=session,
    )
    return success()


@router.post(
    "/v1/admin/biz/cg-test-catalog/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestcatalog:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: CgTestCatalogUpdateRequest,
    service: Annotated[CgTestCatalogService, Depends(get_cg_test_catalog_service)],
) -> ApiResponse[None]:
    await service.update(CgTestCatalogUpdateCommand.model_validate(payload.model_dump()))
    return success()


@router.post(
    "/v1/admin/biz/cg-test-catalog/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestcatalog:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    service: Annotated[CgTestCatalogService, Depends(get_cg_test_catalog_service)],
) -> ApiResponse[None]:
    await service.delete(payload.ids)
    return success()


@router.get(
    "/v1/admin/biz/cg-test-catalog/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestcatalog:detail")),
    ],
    response_model=ApiResponse[CgTestCatalogDetailSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[CgTestCatalogService, Depends(get_cg_test_catalog_service)],
) -> ApiResponse[CgTestCatalogDetailSchema]:
    row = await service.detail(query.id)
    return success(CgTestCatalogDetailSchema.model_validate(row))


@router.get(
    "/v1/admin/biz/cg-test-catalog/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestcatalog:page")),
    ],
    response_model=ApiResponse[PageData[CgTestCatalogSchema]],
)
async def page(
    query: Annotated[CgTestCatalogAdminPageQuery, Depends()],
    service: Annotated[CgTestCatalogService, Depends(get_cg_test_catalog_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[CgTestCatalogSchema]]:
    page_data = await service.page_admin(
        CgTestCatalogPageQuery.model_validate(query.model_dump()),
        session,
    )
    records = [CgTestCatalogSchema.model_validate(row) for row in page_data.records]
    return success(
        PageData(
            size=page_data.size,
            current=page_data.current,
            total=page_data.total,
            pages=page_data.pages,
            records=records,
        )
    )


@router.get(
    "/v1/admin/biz/cg-test-catalog/tree",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestcatalog:list")),
    ],
    response_model=ApiResponse[list[CgTestCatalogTreeNode]],
)
async def tree(
    query: Annotated[KeywordQuery, Depends()],
    service: Annotated[CgTestCatalogService, Depends(get_cg_test_catalog_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[list[CgTestCatalogTreeNode]]:
    nodes = await service.tree(
        CgTestCatalogKeywordQuery(keyword=query.keyword),
        session,
    )

    def to_node(d: dict) -> CgTestCatalogTreeNode:
        children = d.get("children")
        data = {**d, "children": [to_node(c) for c in children] if children else None}
        return CgTestCatalogTreeNode.model_validate(data)

    return success([to_node(n) for n in nodes])
