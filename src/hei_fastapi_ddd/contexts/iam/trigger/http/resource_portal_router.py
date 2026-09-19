""" Author: Charlie

门户资源 HTTP 路由：向 Portal 端公开当前可见资源。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.api.resource_schemas import SysResourceSchema
from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import (
    ResourceService,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.wiring import get_resource_service
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.get(
    "/v1/portal/sys/resources/current",
    response_model=ApiResponse[list[SysResourceSchema]],
)
async def current_resources(
    service: Annotated[ResourceService, Depends(get_resource_service)],
) -> ApiResponse[list[SysResourceSchema]]:
    return success(await service.list_public_portal_resources())
