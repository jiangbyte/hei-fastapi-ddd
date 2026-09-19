"""任务执行基础设施：Redis 锁与仓储实现。"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import time
from datetime import UTC, datetime
from pathlib import Path

from hei_fastapi_ddd.contexts.sys.application.job import cron as cron_util
from hei_fastapi_ddd.contexts.sys.application.job.registry import load_handlers, resolve
from hei_fastapi_ddd.contexts.sys.domain.job.runner import JobRunnerPort
from hei_fastapi_ddd.contexts.sys.infrastructure.job.registry_loader import (
    load_infrastructure_handlers,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.job_repository import (
    JobLogRepositoryImpl,
    JobRepositoryImpl,
)
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.persistence.session import get_session_factory
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.redis.keys import job_run_lock_key
from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.shared.schema.datetime import ensure_utc_datetime

logger = logging.getLogger(__name__)

EXECUTOR_SYSTEM = "system"
LOCK_EXPIRE_SECONDS = 30 * 60
LOCK_ACQUIRE_TIMEOUT_SECONDS = 1
MAX_RESULT_LENGTH = 500


def _resolve_instance_ip() -> str:
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


INSTANCE_IP = _resolve_instance_ip()
INSTANCE_PROCESS_ID = str(os.getpid())
INSTANCE_APP_DIR = str(Path.cwd())

_concurrency_semaphore = asyncio.Semaphore(max(1, settings.job.pool_size))
_running_tasks: set[asyncio.Task] = set()


class JobRunnerImpl:
    """任务执行提交实现。"""

    async def submit(self, job_id: str, *, force: bool, executor: str) -> None:
        task = asyncio.create_task(_execute_with_slot(job_id, force=force, executor=executor))
        _running_tasks.add(task)
        task.add_done_callback(_running_tasks.discard)


async def _execute_with_slot(job_id: str, *, force: bool, executor: str) -> None:
    async with _concurrency_semaphore:
        try:
            await run_job(job_id, force=force, executor=executor)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Job %s execution task failed", job_id)


async def run_job(job_id: str, *, force: bool, executor: str) -> None:
    redis = get_redis()
    if redis is None:
        logger.warning("Job %s executed without Redis lock (Redis unavailable)", job_id)
        await _run_locked(job_id, force=force, executor=executor)
        return
    lock_key = job_run_lock_key(job_id)
    if not await _acquire_lock(redis, lock_key):
        logger.debug("Job %s skipped: lock not acquired", job_id)
        return
    try:
        await _run_locked(job_id, force=force, executor=executor)
    finally:
        await redis.delete(lock_key)


async def _acquire_lock(redis, lock_key: str) -> bool:
    deadline = time.monotonic() + LOCK_ACQUIRE_TIMEOUT_SECONDS
    while True:
        acquired = await redis.set(lock_key, "1", nx=True, ex=LOCK_EXPIRE_SECONDS)
        if acquired:
            return True
        if time.monotonic() >= deadline:
            return False
        await asyncio.sleep(0.1)


async def _run_locked(job_id: str, *, force: bool, executor: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = JobRepositoryImpl(session)
        job = await repo.get_by_id(job_id)
        if job is None or not job.get("enabled"):
            return
        now = datetime.now(UTC)
        if not force and ensure_utc_datetime(job.get("next_run_time")) > now:
            return

        load_handlers()
        load_infrastructure_handlers()
        handler = resolve(str(job.get("handler")))
        started_at = datetime.now(UTC)
        if handler is None:
            await _record_run(
                session,
                job,
                executor=executor,
                success=False,
                result=f"执行失败: 未找到任务处理器: {job.get('handler')}",
                started_at=started_at,
                duration_ms=0,
            )
            return

        param = dict(job.get("params") or {}) if job.get("params") else None
        try:
            run_result = await handler(param)
            result = str(run_result)
            success = True
        except Exception as exc:
            logger.exception("Job %s execution failed", job_id)
            result = f"执行失败: {exc}"
            success = False
        duration_ms = max(0, int((datetime.now(UTC) - started_at).total_seconds() * 1000))
        await _record_run(
            session,
            job,
            executor=executor,
            success=success,
            result=result,
            started_at=started_at,
            duration_ms=duration_ms,
        )


async def _record_run(
    session,
    job: dict,
    *,
    executor: str,
    success: bool,
    result: str,
    started_at: datetime,
    duration_ms: int,
) -> None:
    next_run_time = cron_util.compute_next_run_time(
        str(job.get("trigger_type")),
        str(job.get("trigger_config")),
        started_at,
    )
    job_repo = JobRepositoryImpl(session)
    log_repo = JobLogRepositoryImpl(session)
    async with transactional(session):
        await job_repo.update_run_state(
            str(job["id"]),
            last_run_time=started_at,
            next_run_time=next_run_time,
            last_result=(result or "")[:MAX_RESULT_LENGTH] or None,
        )
        await log_repo.create(
            {
                "job_id": job["id"],
                "params": job.get("params"),
                "started_at": started_at,
                "duration_ms": duration_ms,
                "success": success,
                "result": result,
                "executor": executor,
                "ip": INSTANCE_IP,
                "process_id": INSTANCE_PROCESS_ID,
                "app_dir": INSTANCE_APP_DIR,
            }
        )
    await session.commit()


# 类型检查用
_ = JobRunnerPort
