"""cg_test_order HTTP 适配。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from hei_fastapi_ddd.contexts.biz.api.cg_test_order_schemas import (
    CgTestOrderAdminPageQuery,
    CgTestOrderCreateRequest,
    CgTestOrderItemAdminPageQuery,
    CgTestOrderItemCreateRequest,
    CgTestOrderItemSchema,
    CgTestOrderItemUpdateRequest,
    CgTestOrderSchema,
    CgTestOrderUpdateRequest,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_order.cg_test_order_application_service import (
    CgTestOrderItemService,
    CgTestOrderService,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_order.dto import (
    CgTestOrderCreateCommand,
    CgTestOrderItemCreateCommand,
    CgTestOrderItemPageQuery,
    CgTestOrderItemUpdateCommand,
    CgTestOrderPageQuery,
    CgTestOrderUpdateCommand,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.wiring import (
    get_cg_test_order_item_service,
    get_cg_test_order_service,
)
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_session,
    require_account_type,
    require_permission,
)
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
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
    service: Annotated[CgTestOrderService, Depends(get_cg_test_order_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.create(
        CgTestOrderCreateCommand.model_validate(payload.model_dump()),
        session=session,
    )
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
    service: Annotated[CgTestOrderService, Depends(get_cg_test_order_service)],
) -> ApiResponse[None]:
    await service.update(CgTestOrderUpdateCommand.model_validate(payload.model_dump()))
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
    service: Annotated[CgTestOrderService, Depends(get_cg_test_order_service)],
) -> ApiResponse[None]:
    await service.delete(payload.ids)
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
    service: Annotated[CgTestOrderService, Depends(get_cg_test_order_service)],
) -> ApiResponse[CgTestOrderSchema]:
    return success(CgTestOrderSchema.model_validate(await service.detail(query.id)))


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
    service: Annotated[CgTestOrderService, Depends(get_cg_test_order_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[CgTestOrderSchema]]:
    page_data = await service.page_admin(
        CgTestOrderPageQuery.model_validate(query.model_dump()),
        session,
    )
    records = [CgTestOrderSchema.model_validate(row) for row in page_data.records]
    return success(
        PageData(
            size=page_data.size,
            current=page_data.current,
            total=page_data.total,
            pages=page_data.pages,
            records=records,
        )
    )


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
    service: Annotated[CgTestOrderItemService, Depends(get_cg_test_order_item_service)],
) -> ApiResponse[None]:
    await service.create(CgTestOrderItemCreateCommand.model_validate(payload.model_dump()))
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
    service: Annotated[CgTestOrderItemService, Depends(get_cg_test_order_item_service)],
) -> ApiResponse[None]:
    await service.update(CgTestOrderItemUpdateCommand.model_validate(payload.model_dump()))
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
    service: Annotated[CgTestOrderItemService, Depends(get_cg_test_order_item_service)],
) -> ApiResponse[None]:
    await service.delete(payload.ids)
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
    service: Annotated[CgTestOrderItemService, Depends(get_cg_test_order_item_service)],
) -> ApiResponse[CgTestOrderItemSchema]:
    return success(CgTestOrderItemSchema.model_validate(await service.detail(query.id)))


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
    service: Annotated[CgTestOrderItemService, Depends(get_cg_test_order_item_service)],
) -> ApiResponse[PageData[CgTestOrderItemSchema]]:
    page_data = await service.page_admin(
        CgTestOrderItemPageQuery.model_validate(query.model_dump())
    )
    records = [CgTestOrderItemSchema.model_validate(row) for row in page_data.records]
    return success(
        PageData(
            size=page_data.size,
            current=page_data.current,
            total=page_data.total,
            pages=page_data.pages,
            records=records,
        )
    )
