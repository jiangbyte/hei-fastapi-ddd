""" Author: Charlie

系统字典管理端接口：字典增删改查、分页与树形查询。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.deps.auth import require_account_type, require_permission
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.sys.interfaces.http.dict_schemas import (
    DictAdminPageQuery,
    DictCreateRequest,
    DictIdQuery,
    DictIdsRequest,
    DictTreeQuery,
    DictUpdateRequest,
    SysDictSchema,
    SysDictTreeNode,
)
from hei_fastapi_ddd.contexts.sys.application.dict.dict_application_service import DictService

router = APIRouter()


@router.post(
    "/v1/admin/sys/dicts/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:dict:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: DictCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """新增字典。"""
    await DictService(db).create(payload)
    return success()


@router.post(
    "/v1/admin/sys/dicts/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:dict:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: DictUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """更新字典。"""
    await DictService(db).update(payload)
    return success()


@router.post(
    "/v1/admin/sys/dicts/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:dict:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: DictIdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """批量删除字典。"""
    await DictService(db).delete(payload)
    return success()


@router.get(
    "/v1/admin/sys/dicts/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:dict:detail")),
    ],
    response_model=ApiResponse[SysDictSchema],
)
async def get(
    query: Annotated[DictIdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysDictSchema]:
    """查询字典详情。"""
    return success(await DictService(db).get(query))


@router.get(
    "/v1/admin/sys/dicts/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:dict:page")),
    ],
    response_model=ApiResponse[PageData[SysDictSchema]],
)
async def page(
    query: Annotated[DictAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysDictSchema]]:
    """分页查询字典。"""
    return success(await DictService(db).page_admin(query))


@router.get(
    "/v1/admin/sys/dicts/tree",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        # Depends(require_permission("sys:dict:tree")),
    ],
    response_model=ApiResponse[list[SysDictTreeNode]],
)
async def tree(
    query: Annotated[DictTreeQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[SysDictTreeNode]]:
    """查询字典树。"""
    return success(await DictService(db).list_tree(query))
