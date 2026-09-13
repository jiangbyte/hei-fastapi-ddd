""" Author: Charlie

展示图公开端接口：列表查询与交互计数。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.schema.base import IdQuery
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.sys.interfaces.http.banner_schemas import (
    BannerPublicListQuery,
    SysBannerSchema,
)
from hei_fastapi_ddd.contexts.sys.application.banner.banner_application_service import BannerService

router = APIRouter()


@router.get("/v1/portal/sys/banners/list", response_model=ApiResponse[list[SysBannerSchema]])
async def list_public_banners(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[BannerPublicListQuery, Depends()],
) -> ApiResponse[list[SysBannerSchema]]:
    """公开端按位置查询可见展示图列表。"""
    return success(await BannerService(db).list_public(query))


@router.post("/v1/portal/sys/banners/interaction", response_model=ApiResponse[None])
async def record_banner_interaction(
    payload: IdQuery,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """记录一次展示图交互，用于异步累加交互次数。"""
    await BannerService(db).record_interaction(payload)
    return success()
