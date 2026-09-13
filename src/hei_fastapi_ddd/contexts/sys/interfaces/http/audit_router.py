""" Author: Charlie

操作审计后台接口：分页查询与详情查询，仅管理员可访问。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.audit.audit_application_service import (
    OperationAuditService,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.audit_schemas import (
    OperationAuditPageQuery,
    OperationAuditRecord,
)
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_session,
    require_account_type,
    require_permission,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.schema.base import IdQuery
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.get(
    "/v1/admin/sys/audit/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:audit:page")),
    ],
    response_model=ApiResponse[PageData[OperationAuditRecord]],
    response_model_exclude_none=False,
)
async def page(
    query: Annotated[OperationAuditPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[OperationAuditRecord]]:
    """后台分页查询操作审计日志。"""
    return success(await OperationAuditService(db).page_admin(query))


@router.get(
    "/v1/admin/sys/audit/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:audit:detail")),
    ],
    response_model=ApiResponse[OperationAuditRecord],
    response_model_exclude_none=False,
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[OperationAuditRecord]:
    """按主键查询单条操作审计日志详情。"""
    return success(await OperationAuditService(db).detail(query))


@router.get(
    "/v1/admin/sys/audit/my-page",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[PageData[OperationAuditRecord]],
    response_model_exclude_none=False,
)
async def my_page(
    query: Annotated[OperationAuditPageQuery, Depends()],
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[OperationAuditRecord]]:
    """当前管理员本人审计日志分页（无需审计管理权限）。"""
    return success(
        await OperationAuditService(db).my_page(query, session.account_id)
    )


@router.get(
    "/v1/admin/sys/audit/my-detail",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[OperationAuditRecord],
    response_model_exclude_none=False,
)
async def my_detail(
    query: Annotated[IdQuery, Depends()],
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[OperationAuditRecord]:
    """当前管理员本人审计详情。"""
    return success(
        await OperationAuditService(db).my_detail(query.id, session.account_id)
    )
