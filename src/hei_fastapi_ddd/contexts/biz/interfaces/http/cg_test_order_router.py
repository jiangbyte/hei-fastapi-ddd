"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:54
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.biz.application.cg_test_order.cg_test_order_application_service import (
    CgTestOrderItemService,
    CgTestOrderService,
)
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_order_schemas import (
    CgTestOrderAdminPageQuery,
    CgTestOrderCreateRequest,
    CgTestOrderItemAdminPageQuery,
    CgTestOrderItemCreateRequest,
    CgTestOrderItemSchema,
    CgTestOrderItemUpdateRequest,
    CgTestOrderSchema,
    CgTestOrderUpdateRequest,
)
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_session,
    require_account_type,
    require_permission,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.schema.base import (
    IdQuery,
    IdsRequest,
)
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.post(
    "/v1/admin/biz/cg-test-order/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestorder:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: CgTestOrderCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await CgTestOrderService(db).create(payload, session=session)
    return success()


@router.post(
    "/v1/admin/biz/cg-test-order/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestorder:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: CgTestOrderUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestOrderService(db).update(payload)
    return success()


@router.post(
    "/v1/admin/biz/cg-test-order/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestorder:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestOrderService(db).delete(payload)
    return success()


@router.get(
    "/v1/admin/biz/cg-test-order/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestorder:detail")),
    ],
    response_model=ApiResponse[CgTestOrderSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[CgTestOrderSchema]:
    return success(await CgTestOrderService(db).detail(query))


@router.get(
    "/v1/admin/biz/cg-test-order/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestorder:page")),
    ],
    response_model=ApiResponse[PageData[CgTestOrderSchema]],
)
async def page(
    query: Annotated[CgTestOrderAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[CgTestOrderSchema]]:
    return success(await CgTestOrderService(db).page_admin(query, session))


@router.post(
    "/v1/admin/biz/cg-test-order/children/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestorder:create")),
    ],
    response_model=ApiResponse[None],
)
async def create_child(
    payload: CgTestOrderItemCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestOrderItemService(db).create(payload)
    return success()


@router.post(
    "/v1/admin/biz/cg-test-order/children/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestorder:update")),
    ],
    response_model=ApiResponse[None],
)
async def update_child(
    payload: CgTestOrderItemUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestOrderItemService(db).update(payload)
    return success()


@router.post(
    "/v1/admin/biz/cg-test-order/children/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestorder:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete_child(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    await CgTestOrderItemService(db).delete(payload)
    return success()


@router.get(
    "/v1/admin/biz/cg-test-order/children/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestorder:detail")),
    ],
    response_model=ApiResponse[CgTestOrderItemSchema],
)
async def child_detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[CgTestOrderItemSchema]:
    return success(await CgTestOrderItemService(db).detail(query))


@router.get(
    "/v1/admin/biz/cg-test-order/children/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestorder:page")),
    ],
    response_model=ApiResponse[PageData[CgTestOrderItemSchema]],
)
async def child_page(
    query: Annotated[CgTestOrderItemAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[CgTestOrderItemSchema]]:
    return success(await CgTestOrderItemService(db).page_admin(query))
