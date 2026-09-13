""" Author: Charlie

部门管理 HTTP 路由：部门 CRUD 与部门树查询。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.dept.dept_application_service import DeptService
from hei_fastapi_ddd.contexts.iam.interfaces.http.dept_schemas import (
    DeptAdminPageQuery,
    DeptCreateRequest,
    DeptTreeNode,
    DeptUpdateRequest,
    SysDeptSchema,
)
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_session,
    require_account_type,
    require_permission,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.post(
    "/v1/admin/sys/depts/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: DeptCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await DeptService(db).create(payload, session)
    return success()


@router.post(
    "/v1/admin/sys/depts/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: DeptUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await DeptService(db).update(payload, session)
    return success()


@router.post(
    "/v1/admin/sys/depts/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await DeptService(db).delete(payload, session)
    return success()


@router.get(
    "/v1/admin/sys/depts/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:detail")),
    ],
    response_model=ApiResponse[SysDeptSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysDeptSchema]:
    return success(await DeptService(db).detail(query, session))


@router.get(
    "/v1/admin/sys/depts/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:page")),
    ],
    response_model=ApiResponse[PageData[SysDeptSchema]],
)
async def page(
    query: Annotated[DeptAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[SysDeptSchema]]:
    return success(await DeptService(db).page_admin(query, session))


@router.get(
    "/v1/admin/sys/depts/tree",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:tree")),
    ],
    response_model=ApiResponse[list[DeptTreeNode]],
)
async def list_dept_tree(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[list[DeptTreeNode]]:
    return success(await DeptService(db).list_dept_tree(session))
