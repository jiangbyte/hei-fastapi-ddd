""" Author: Charlie

系统字典公开端接口：树形查询。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.sys.interfaces.http.dict_schemas import DictTreeQuery, SysDictTreeNode
from hei_fastapi_ddd.contexts.sys.application.dict.dict_application_service import DictService

router = APIRouter()


@router.get(
    "/v1/portal/sys/dicts/tree",
    response_model=ApiResponse[list[SysDictTreeNode]],
)
async def tree(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[DictTreeQuery, Depends()],
) -> ApiResponse[list[SysDictTreeNode]]:
    """公开端按分类查询字典树。"""
    return success(await DictService(db).list_tree(query))
