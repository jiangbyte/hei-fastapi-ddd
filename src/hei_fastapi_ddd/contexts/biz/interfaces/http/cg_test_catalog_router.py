"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:53
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
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_catalog_schemas import (
    CgTestCatalogAdminPageQuery,
    CgTestCatalogCreateRequest,
    CgTestCatalogSchema,
    CgTestCatalogTreeNode,
    CgTestCatalogUpdateRequest,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_catalog.cg_test_catalog_application_service import (
    CgTestCatalogService,
)

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
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await CgTestCatalogService(db).create(payload, session=session)
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
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestCatalogService(db).update(payload)
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
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestCatalogService(db).delete(payload)
    return success()


@router.get(
    "/v1/admin/biz/cg-test-catalog/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestcatalog:detail")),
    ],
    response_model=ApiResponse[CgTestCatalogSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[CgTestCatalogSchema]:
    return success(await CgTestCatalogService(db).detail(query))


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
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[CgTestCatalogSchema]]:
    return success(await CgTestCatalogService(db).page_admin(query, session))


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
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[list[CgTestCatalogTreeNode]]:
    return success(await CgTestCatalogService(db).tree(query, session))
