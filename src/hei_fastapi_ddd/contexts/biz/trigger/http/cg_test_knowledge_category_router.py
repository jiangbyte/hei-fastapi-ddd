"""知识分类 HTTP 适配。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from hei_fastapi_ddd.contexts.biz.api.cg_test_knowledge_category_schemas import (
    CgTestKnowledgeCategoryAdminPageQuery,
    CgTestKnowledgeCategoryCreateRequest,
    CgTestKnowledgeCategoryDetailSchema,
    CgTestKnowledgeCategorySchema,
    CgTestKnowledgeCategoryTreeNode,
    CgTestKnowledgeCategoryUpdateRequest,
    CgTestKnowledgeDocAdminPageQuery,
    CgTestKnowledgeDocCreateRequest,
    CgTestKnowledgeDocSchema,
    CgTestKnowledgeDocUpdateRequest,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_knowledge_category.cg_test_knowledge_category_application_service import (
    CgTestKnowledgeCategoryService,
    CgTestKnowledgeDocService,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_knowledge_category.dto import (
    CgTestKnowledgeCategoryCreateCommand,
    CgTestKnowledgeCategoryKeywordQuery,
    CgTestKnowledgeCategoryPageQuery,
    CgTestKnowledgeCategoryUpdateCommand,
    CgTestKnowledgeDocCreateCommand,
    CgTestKnowledgeDocPageQuery,
    CgTestKnowledgeDocUpdateCommand,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.wiring import (
    get_cg_test_knowledge_category_service,
    get_cg_test_knowledge_doc_service,
)
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
    "/v1/admin/biz/cg-test-knowledge-category/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: CgTestKnowledgeCategoryCreateRequest,
    service: Annotated[CgTestKnowledgeCategoryService, Depends(get_cg_test_knowledge_category_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.create(
        CgTestKnowledgeCategoryCreateCommand.model_validate(payload.model_dump()),
        session=session,
    )
    return success()


@router.post(
    "/v1/admin/biz/cg-test-knowledge-category/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: CgTestKnowledgeCategoryUpdateRequest,
    service: Annotated[CgTestKnowledgeCategoryService, Depends(get_cg_test_knowledge_category_service)],
) -> ApiResponse[None]:
    await service.update(
        CgTestKnowledgeCategoryUpdateCommand.model_validate(payload.model_dump())
    )
    return success()


@router.post(
    "/v1/admin/biz/cg-test-knowledge-category/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    service: Annotated[CgTestKnowledgeCategoryService, Depends(get_cg_test_knowledge_category_service)],
) -> ApiResponse[None]:
    await service.delete(payload.ids)
    return success()


@router.get(
    "/v1/admin/biz/cg-test-knowledge-category/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:detail")),
    ],
    response_model=ApiResponse[CgTestKnowledgeCategoryDetailSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[CgTestKnowledgeCategoryService, Depends(get_cg_test_knowledge_category_service)],
) -> ApiResponse[CgTestKnowledgeCategoryDetailSchema]:
    return success(CgTestKnowledgeCategoryDetailSchema.model_validate(await service.detail(query.id)))


@router.get(
    "/v1/admin/biz/cg-test-knowledge-category/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:page")),
    ],
    response_model=ApiResponse[PageData[CgTestKnowledgeCategorySchema]],
)
async def page(
    query: Annotated[CgTestKnowledgeCategoryAdminPageQuery, Depends()],
    service: Annotated[CgTestKnowledgeCategoryService, Depends(get_cg_test_knowledge_category_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[CgTestKnowledgeCategorySchema]]:
    page_data = await service.page_admin(
        CgTestKnowledgeCategoryPageQuery.model_validate(query.model_dump()),
        session,
    )
    records = [CgTestKnowledgeCategorySchema.model_validate(row) for row in page_data.records]
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
    "/v1/admin/biz/cg-test-knowledge-category/tree",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:list")),
    ],
    response_model=ApiResponse[list[CgTestKnowledgeCategoryTreeNode]],
)
async def tree(
    query: Annotated[KeywordQuery, Depends()],
    service: Annotated[CgTestKnowledgeCategoryService, Depends(get_cg_test_knowledge_category_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[list[CgTestKnowledgeCategoryTreeNode]]:
    nodes = await service.tree(
        CgTestKnowledgeCategoryKeywordQuery(keyword=query.keyword),
        session,
    )

    def to_node(d: dict) -> CgTestKnowledgeCategoryTreeNode:
        children = d.get("children")
        data = {**d, "children": [to_node(c) for c in children] if children else None}
        return CgTestKnowledgeCategoryTreeNode.model_validate(data)

    return success([to_node(n) for n in nodes])


@router.post(
    "/v1/admin/biz/cg-test-knowledge-category/children/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:create")),
    ],
    response_model=ApiResponse[None],
)
async def create_doc(
    payload: CgTestKnowledgeDocCreateRequest,
    service: Annotated[CgTestKnowledgeDocService, Depends(get_cg_test_knowledge_doc_service)],
) -> ApiResponse[None]:
    await service.create(CgTestKnowledgeDocCreateCommand.model_validate(payload.model_dump()))
    return success()


@router.post(
    "/v1/admin/biz/cg-test-knowledge-category/children/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:update")),
    ],
    response_model=ApiResponse[None],
)
async def update_doc(
    payload: CgTestKnowledgeDocUpdateRequest,
    service: Annotated[CgTestKnowledgeDocService, Depends(get_cg_test_knowledge_doc_service)],
) -> ApiResponse[None]:
    await service.update(CgTestKnowledgeDocUpdateCommand.model_validate(payload.model_dump()))
    return success()


@router.post(
    "/v1/admin/biz/cg-test-knowledge-category/children/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete_doc(
    payload: IdsRequest,
    service: Annotated[CgTestKnowledgeDocService, Depends(get_cg_test_knowledge_doc_service)],
) -> ApiResponse[None]:
    await service.delete(payload.ids)
    return success()


@router.get(
    "/v1/admin/biz/cg-test-knowledge-category/children/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:detail")),
    ],
    response_model=ApiResponse[CgTestKnowledgeDocSchema],
)
async def doc_detail(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[CgTestKnowledgeDocService, Depends(get_cg_test_knowledge_doc_service)],
) -> ApiResponse[CgTestKnowledgeDocSchema]:
    return success(CgTestKnowledgeDocSchema.model_validate(await service.detail(query.id)))


@router.get(
    "/v1/admin/biz/cg-test-knowledge-category/children/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:page")),
    ],
    response_model=ApiResponse[PageData[CgTestKnowledgeDocSchema]],
)
async def doc_page(
    query: Annotated[CgTestKnowledgeDocAdminPageQuery, Depends()],
    service: Annotated[CgTestKnowledgeDocService, Depends(get_cg_test_knowledge_doc_service)],
) -> ApiResponse[PageData[CgTestKnowledgeDocSchema]]:
    page_data = await service.page_admin(
        CgTestKnowledgeDocPageQuery.model_validate(query.model_dump())
    )
    records = [CgTestKnowledgeDocSchema.model_validate(row) for row in page_data.records]
    return success(
        PageData(
            size=page_data.size,
            current=page_data.current,
            total=page_data.total,
            pages=page_data.pages,
            records=records,
        )
    )
