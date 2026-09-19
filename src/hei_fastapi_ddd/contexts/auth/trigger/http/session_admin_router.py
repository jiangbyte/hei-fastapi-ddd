""" Author: Charlie

会话管理路由：在线会话分析、分页查询、token 列表与强制下线端点。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.auth.api.session_schemas import (
    SessionAccountItem,
    SessionAnalysisResponse,
    SessionExitRequest,
    SessionPageQuery,
    SessionTokenExitRequest,
    SessionTokenInfo,
    SessionTokensQuery,
)
from hei_fastapi_ddd.contexts.auth.application.session_admin_service import SessionAdminService
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import require_account_type, require_permission
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.get(
    "/v1/admin/auth/sessions/analysis",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("auth:session:analysis")),
    ],
    response_model=ApiResponse[SessionAnalysisResponse],
)
async def analysis(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SessionAnalysisResponse]:
    """在线会话统计概览端点。"""
    return success(await get_session_admin_service(db).analysis())


@router.get(
    "/v1/admin/auth/sessions/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("auth:session:page")),
    ],
    response_model=ApiResponse[PageData[SessionAccountItem]],
)
async def page(
    query: Annotated[SessionPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SessionAccountItem]]:
    """在线会话分页查询端点。"""
    return success(await get_session_admin_service(db).page(query))


@router.get(
    "/v1/admin/auth/sessions/tokens",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("auth:session:tokenlist")),
    ],
    response_model=ApiResponse[list[SessionTokenInfo]],
)
async def tokens(
    query: Annotated[SessionTokensQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[SessionTokenInfo]]:
    """查询指定账户的在线 token 列表端点。"""
    return success(await get_session_admin_service(db).tokens(query))


@router.post(
    "/v1/admin/auth/sessions/exit",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("auth:session:exit")),
    ],
    response_model=ApiResponse[None],
)
async def exit_sessions(
    payload: SessionExitRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """按账户批量强制下线端点。"""
    await get_session_admin_service(db).exit_sessions(payload.targets)
    return success()


@router.post(
    "/v1/admin/auth/sessions/token/exit",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("auth:session:tokenexit")),
    ],
    response_model=ApiResponse[None],
)
async def exit_tokens(
    payload: SessionTokenExitRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """按 token 批量强制下线端点。"""
    await get_session_admin_service(db).exit_tokens(payload.tokens)
    return success()
