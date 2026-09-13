""" Author: Charlie

门户资源 HTTP 路由：向 Portal 端公开当前可见资源。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.iam.interfaces.http.resource_schemas import SysResourceSchema
from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import ResourceService

router = APIRouter()


@router.get(
    "/v1/portal/sys/resources/current",
    response_model=ApiResponse[list[SysResourceSchema]],
)
async def current_resources(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[SysResourceSchema]]:
    return success(await ResourceService(db).list_public_portal_resources())
