""" Author: Charlie

任务调度器：进程内 asyncio 后台任务，周期扫描 sys_job 到期任务并提交执行
（对齐 hei-boot JobTaskScheduler）。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from hei_fastapi_ddd.contexts.sys.application.job.registry import load_handlers
from hei_fastapi_ddd.contexts.sys.infrastructure.job.registry_loader import load_infrastructure_handlers
from hei_fastapi_ddd.contexts.sys.infrastructure.job.runner import EXECUTOR_SYSTEM, JobRunnerImpl
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.job_repository import JobRepositoryImpl
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.persistence.session import get_session_factory

logger = logging.getLogger(__name__)

# 单轮最多扫描条数，防到期任务积压风暴（对齐 hei-boot MAX_SCAN_LIMIT=50）。
MAX_SCAN_LIMIT = 50

_scheduler_task: asyncio.Task | None = None


async def start_job_scheduler() -> None:
    """启动任务调度器后台任务（幂等；首次加载全部业务处理器注册）。"""
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        return
    load_handlers()
    load_infrastructure_handlers()
    loop = asyncio.get_running_loop()
    _scheduler_task = loop.create_task(_scan_loop())
    logger.info(
        "job scheduler started: scan_interval_ms=%s pool_size=%s",
        settings.job.scan_interval_ms,
        settings.job.pool_size,
    )


async def stop_job_scheduler() -> None:
    """停止任务调度器后台任务。"""
    global _scheduler_task
    task = _scheduler_task
    _scheduler_task = None
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("job scheduler stopped")


async def _scan_loop() -> None:
    """周期扫描到期任务并提交执行，单轮失败不影响下一轮。"""
    while True:
        try:
            await _scan_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("job scheduler scan failed")
        await asyncio.sleep(max(0.1, settings.job.scan_interval_ms / 1000))


async def _scan_once() -> None:
    """扫描到期任务并逐个提交执行。"""
    factory = get_session_factory()
    async with factory() as session:
        jobs = await JobRepositoryImpl(session).find_due_jobs(
            datetime.now(UTC), limit=MAX_SCAN_LIMIT
        )
    runner = JobRunnerImpl()
    for job in jobs:
        await runner.submit(str(job["id"]), force=False, executor=EXECUTOR_SYSTEM)
