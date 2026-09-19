"""
cg_test_activity HTTP 触发器：Schema ↔ 应用 DTO，经 wiring 注入服务。
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from hei_fastapi_ddd.contexts.biz.api.cg_test_activity_schemas import (
    CgTestActivityAdminPageQuery,
    CgTestActivityCreateRequest,
    CgTestActivitySchema,
    CgTestActivityUpdateRequest,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_activity.cg_test_activity_application_service import (
    CgTestActivityService,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_activity.dto import (
    CgTestActivityCreateCommand,
    CgTestActivityPageQuery,
    CgTestActivityUpdateCommand,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.wiring import get_cg_test_activity_service
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_session,
    require_account_type,
    require_permission,
)
from hei_fastapi_ddd.shared.schema.base import (
    IdQuery,
    IdsRequest,
)
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.post(
    "/v1/admin/biz/cg-test-activity/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestactivity:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: CgTestActivityCreateRequest,
    service: Annotated[CgTestActivityService, Depends(get_cg_test_activity_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.create(
        CgTestActivityCreateCommand.model_validate(payload.model_dump()),
        session=session,
    )
    return success()


@router.post(
    "/v1/admin/biz/cg-test-activity/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestactivity:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: CgTestActivityUpdateRequest,
    service: Annotated[CgTestActivityService, Depends(get_cg_test_activity_service)],
) -> ApiResponse[None]:
    await service.update(CgTestActivityUpdateCommand.model_validate(payload.model_dump()))
    return success()


@router.post(
    "/v1/admin/biz/cg-test-activity/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestactivity:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    service: Annotated[CgTestActivityService, Depends(get_cg_test_activity_service)],
) -> ApiResponse[None]:
    await service.delete(list(payload.ids))
    return success()


@router.get(
    "/v1/admin/biz/cg-test-activity/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestactivity:detail")),
    ],
    response_model=ApiResponse[CgTestActivitySchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[CgTestActivityService, Depends(get_cg_test_activity_service)],
) -> ApiResponse[CgTestActivitySchema]:
    row = await service.detail(query.id)
    return success(CgTestActivitySchema.model_validate(row))


@router.get(
    "/v1/admin/biz/cg-test-activity/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("biz:cgtestactivity:page")),
    ],
    response_model=ApiResponse[PageData[CgTestActivitySchema]],
)
async def page(
    query: Annotated[CgTestActivityAdminPageQuery, Depends()],
    service: Annotated[CgTestActivityService, Depends(get_cg_test_activity_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[CgTestActivitySchema]]:
    page_data = await service.page_admin(
        CgTestActivityPageQuery.model_validate(query.model_dump()),
        session,
    )
    records = [CgTestActivitySchema.model_validate(row) for row in page_data.records]
    return success(
        PageData(
            size=page_data.size,
            current=page_data.current,
            total=page_data.total,
            pages=page_data.pages,
            records=records,
        )
    )
