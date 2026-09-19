""" Author: Charlie

系统字典公开端接口：树形查询。
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from hei_fastapi_ddd.contexts.sys.api.dict_schemas import DictTreeQuery, SysDictTreeNode
from hei_fastapi_ddd.contexts.sys.application.dict.dict_application_service import (
    DictService,
    build_tree_nodes_from_records,
)
from hei_fastapi_ddd.contexts.sys.application.dict.dto import DictTreeQuery as DictTreeQueryDto
from hei_fastapi_ddd.contexts.sys.infrastructure.wiring import get_dict_service
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.get(
    "/v1/portal/sys/dicts/tree",
    response_model=ApiResponse[list[SysDictTreeNode]],
)
async def tree(
    query: Annotated[DictTreeQuery, Depends()],
    service: Annotated[DictService, Depends(get_dict_service)],
) -> ApiResponse[list[SysDictTreeNode]]:
    """公开端按分类查询字典树。"""
    records = build_tree_nodes_from_records(
        await service.list_tree(DictTreeQueryDto.model_validate(query.model_dump()))
    )
    return success([SysDictTreeNode.model_validate(node) for node in records])
