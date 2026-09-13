""" Author: Charlie

定时任务管理端接口：任务 CRUD、启停、立即执行与执行日志分页（对齐 hei-boot）。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.job.job_application_service import JobService
from hei_fastapi_ddd.contexts.sys.interfaces.http.job_schemas import (
    JobAdminPageQuery,
    JobCreateRequest,
    JobEnabledRequest,
    JobLogAdminPageQuery,
    JobUpdateRequest,
    SysJobLogSchema,
    SysJobSchema,
)
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_account,
    require_account_type,
    require_permission,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.get(
    "/v1/admin/sys/jobs/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:job:page")),
    ],
    response_model=ApiResponse[PageData[SysJobSchema]],
)
async def page(
    query: Annotated[JobAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysJobSchema]]:
    """分页查询任务。"""
    return success(await JobService(db).page_admin(query))


@router.get(
    "/v1/admin/sys/jobs/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:job:detail")),
    ],
    response_model=ApiResponse[SysJobSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysJobSchema]:
    """查询任务详情。"""
    return success(await JobService(db).detail(query))


@router.post(
    "/v1/admin/sys/jobs/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:job:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: JobCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """新增任务。"""
    await JobService(db).create(payload)
    return success()


@router.post(
    "/v1/admin/sys/jobs/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:job:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: JobUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """更新任务。"""
    await JobService(db).update(payload)
    return success()


@router.post(
    "/v1/admin/sys/jobs/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:job:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """批量删除任务。"""
    await JobService(db).delete(payload)
    return success()


@router.post(
    "/v1/admin/sys/jobs/enabled",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:job:update")),
    ],
    response_model=ApiResponse[None],
)
async def enabled(
    payload: JobEnabledRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """启停任务。"""
    await JobService(db).update_enabled(payload)
    return success()


@router.post(
    "/v1/admin/sys/jobs/run",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:job:run")),
    ],
    response_model=ApiResponse[None],
)
async def run(
    payload: IdQuery,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    account=Depends(get_current_account),
) -> ApiResponse[None]:
    """立即执行任务（异步触发，结果见执行日志）。"""
    await JobService(db).run_now(payload, executor=str(account.id))
    return success()


@router.get(
    "/v1/admin/sys/job-logs/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:joblog:page")),
    ],
    response_model=ApiResponse[PageData[SysJobLogSchema]],
)
async def log_page(
    query: Annotated[JobLogAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysJobLogSchema]]:
    """分页查询任务执行记录。"""
    return success(await JobService(db).page_logs(query))
