"""展示图公开端接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from hei_fastapi_ddd.contexts.sys.api.banner_schemas import (
    BannerPublicListQuery,
    SysBannerSchema,
)
from hei_fastapi_ddd.contexts.sys.application.banner.banner_application_service import (
    BannerService,
)
from hei_fastapi_ddd.contexts.sys.application.banner.dto import (
    BannerPublicListQuery as BannerPublicListQueryDto,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.wiring import get_banner_service
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import get_optional_session
from hei_fastapi_ddd.shared.schema.base import IdQuery
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.get("/v1/portal/sys/banners/list", response_model=ApiResponse[list[SysBannerSchema]])
async def list_public_banners(
    query: Annotated[BannerPublicListQuery, Depends()],
    service: Annotated[BannerService, Depends(get_banner_service)],
    session: Annotated[SessionPayload | None, Depends(get_optional_session)] = None,
) -> ApiResponse[list[SysBannerSchema]]:
    account_type = AccountType(session.account_type) if session else AccountType.PORTAL
    rows = await service.list_visible(
        BannerPublicListQueryDto.model_validate(query.model_dump()),
        account_type=account_type,
    )
    return success([SysBannerSchema.model_validate(r) for r in rows])


@router.post("/v1/portal/sys/banners/interaction", response_model=ApiResponse[None])
async def record_banner_interaction(
    payload: IdQuery,
    service: Annotated[BannerService, Depends(get_banner_service)],
    session: Annotated[SessionPayload | None, Depends(get_optional_session)] = None,
) -> ApiResponse[None]:
    account_type = AccountType(session.account_type) if session else AccountType.PORTAL
    await service.record_interaction(payload.id, account_type=account_type)
    return success()
