"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:55
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.schema.base import (
    IdQuery,
    IdsRequest,
    KeywordQuery,
)
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.deps.auth import get_current_session, require_account_type, require_permission
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_knowledge_category_schemas import (
    CgTestKnowledgeCategoryAdminPageQuery,
    CgTestKnowledgeCategoryCreateRequest,
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
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await CgTestKnowledgeCategoryService(db).create(payload, session=session)
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
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestKnowledgeCategoryService(db).update(payload)
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
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestKnowledgeCategoryService(db).delete(payload)
    return success()


@router.get(
    "/v1/admin/biz/cg-test-knowledge-category/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:detail")),
    ],
    response_model=ApiResponse[CgTestKnowledgeCategorySchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[CgTestKnowledgeCategorySchema]:
    return success(await CgTestKnowledgeCategoryService(db).detail(query))


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
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[CgTestKnowledgeCategorySchema]]:
    return success(await CgTestKnowledgeCategoryService(db).page_admin(query, session))


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
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[list[CgTestKnowledgeCategoryTreeNode]]:
    return success(await CgTestKnowledgeCategoryService(db).tree(query, session))


@router.post(
    "/v1/admin/biz/cg-test-knowledge-category/children/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:create")),
    ],
    response_model=ApiResponse[None],
)
async def create_child(
    payload: CgTestKnowledgeDocCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestKnowledgeDocService(db).create(payload)
    return success()


@router.post(
    "/v1/admin/biz/cg-test-knowledge-category/children/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:update")),
    ],
    response_model=ApiResponse[None],
)
async def update_child(
    payload: CgTestKnowledgeDocUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestKnowledgeDocService(db).update(payload)
    return success()


@router.post(
    "/v1/admin/biz/cg-test-knowledge-category/children/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete_child(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestKnowledgeDocService(db).delete(payload)
    return success()


@router.get(
    "/v1/admin/biz/cg-test-knowledge-category/children/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:detail")),
    ],
    response_model=ApiResponse[CgTestKnowledgeDocSchema],
)
async def child_detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[CgTestKnowledgeDocSchema]:
    return success(await CgTestKnowledgeDocService(db).detail(query))


@router.get(
    "/v1/admin/biz/cg-test-knowledge-category/children/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestknowledgecategory:page")),
    ],
    response_model=ApiResponse[PageData[CgTestKnowledgeDocSchema]],
)
async def child_page(
    query: Annotated[CgTestKnowledgeDocAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[CgTestKnowledgeDocSchema]]:
    return success(await CgTestKnowledgeDocService(db).page_admin(query))
