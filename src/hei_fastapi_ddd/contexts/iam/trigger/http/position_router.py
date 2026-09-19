"""Author: Charlie

职位管理 HTTP 路由：Schema ↔ Command，经 wiring 注入服务。
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from hei_fastapi_ddd.contexts.iam.api.position_schemas import (
    PositionAdminPageQuery,
    PositionCreateRequest,
    PositionUpdateRequest,
    SysPositionSchema,
)
from hei_fastapi_ddd.contexts.iam.application.position.dto import (
    PositionCreateCommand,
    PositionPageQuery,
    PositionUpdateCommand,
)
from hei_fastapi_ddd.contexts.iam.application.position.position_application_service import (
    PositionService,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.wiring import get_position_service
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_session,
    require_account_type,
    require_permission,
)
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, to_schema, to_schema_list
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.post(
    "/v1/admin/sys/positions/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:position:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: PositionCreateRequest,
    service: Annotated[PositionService, Depends(get_position_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.create(
        PositionCreateCommand.model_validate(payload.model_dump()),
        session=session,
    )
    return success()


@router.post(
    "/v1/admin/sys/positions/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:position:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: PositionUpdateRequest,
    service: Annotated[PositionService, Depends(get_position_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.update(
        PositionUpdateCommand.model_validate(payload.model_dump()),
        session=session,
    )
    return success()


@router.post(
    "/v1/admin/sys/positions/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:position:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    service: Annotated[PositionService, Depends(get_position_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.delete(payload, session=session)
    return success()


@router.get(
    "/v1/admin/sys/positions/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:position:detail")),
    ],
    response_model=ApiResponse[SysPositionSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[PositionService, Depends(get_position_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysPositionSchema]:
    row = await service.detail(query, session=session)
    return success(to_schema(SysPositionSchema, row))


@router.get(
    "/v1/admin/sys/positions/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:position:page")),
    ],
    response_model=ApiResponse[PageData[SysPositionSchema]],
)
async def page(
    query: Annotated[PositionAdminPageQuery, Depends()],
    service: Annotated[PositionService, Depends(get_position_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[SysPositionSchema]]:
    page_data = await service.page_admin(
        PositionPageQuery.model_validate(query.model_dump()),
        session=session,
    )
    return success(
        PageData(
            records=to_schema_list(SysPositionSchema, page_data.records),
            total=page_data.total,
            current=page_data.current,
            size=page_data.size,
        )
    )
