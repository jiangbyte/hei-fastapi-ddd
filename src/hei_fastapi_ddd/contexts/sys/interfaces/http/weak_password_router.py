""" Author: Charlie

弱密码库管理端接口：弱密码的增删改查与列表（无业务层，直接走仓储）。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.persistence.models.sys_weak_password import SysWeakPassword
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, to_schema, to_schema_list
from hei_fastapi_ddd.shared.deps.auth import require_account_type, require_permission
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.weak_password_repository import WeakPasswordRepository
from hei_fastapi_ddd.contexts.sys.interfaces.http.weak_password_schemas import (
    SysWeakPasswordSchema,
    WeakPasswordAdminPageQuery,
    WeakPasswordCreateRequest,
    WeakPasswordListQuery,
    WeakPasswordUpdateRequest,
)

router = APIRouter()


@router.post(
    "/v1/admin/sys/weak-password/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: WeakPasswordCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """新增弱密码。"""
    repo = WeakPasswordRepository(db)
    password = payload.password.strip()
    await repo.create(payload)
    entity = (
        await db.execute(select(SysWeakPassword).where(SysWeakPassword.password == password).limit(1))
    ).scalar_one()
    audit_snapshots.created_entity(entity)
    return success()


@router.post(
    "/v1/admin/sys/weak-password/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: WeakPasswordUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """更新弱密码。"""
    repo = WeakPasswordRepository(db)
    entity = await repo.get_required(payload.id)
    audit_snapshots.before_entity(entity)
    await repo.update(payload)
    await db.refresh(entity)
    audit_snapshots.after_entity(entity)
    return success()


@router.post(
    "/v1/admin/sys/weak-password/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """批量删除弱密码。"""
    repo = WeakPasswordRepository(db)
    unique_ids = list(dict.fromkeys(payload.ids))
    entities = [
        entity
        for entity_id in unique_ids
        if (entity := await repo.get_by_id(entity_id)) is not None
    ]
    audit_snapshots.deleted_all(entities)
    await repo.delete_many(payload.ids)
    return success()


@router.get(
    "/v1/admin/sys/weak-password/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:detail")),
    ],
    response_model=ApiResponse[SysWeakPasswordSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysWeakPasswordSchema]:
    """查询弱密码详情。"""
    return success(
        to_schema(SysWeakPasswordSchema, await WeakPasswordRepository(db).get_required(query.id))
    )


@router.get(
    "/v1/admin/sys/weak-password/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:page")),
    ],
    response_model=ApiResponse[PageData[SysWeakPasswordSchema]],
)
async def page(
    query: Annotated[WeakPasswordAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysWeakPasswordSchema]]:
    """分页查询弱密码。"""
    items, total = await WeakPasswordRepository(db).page_admin(query)
    return success(build_page(query, total, to_schema_list(SysWeakPasswordSchema, items)))


@router.get(
    "/v1/admin/sys/weak-password/list",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:list")),
    ],
    response_model=ApiResponse[list[SysWeakPasswordSchema]],
)
async def list_all(
    query: Annotated[WeakPasswordListQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[SysWeakPasswordSchema]]:
    """列出全部弱密码。"""
    items = await WeakPasswordRepository(db).list_all(query)
    return success(to_schema_list(SysWeakPasswordSchema, items))
