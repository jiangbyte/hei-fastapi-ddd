""" Author: Charlie

任务执行引擎：Redis 锁串行化同一任务，执行后事务内更新任务状态并写执行日志
（对齐 hei-boot JobExecutionService）。
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import time
from datetime import UTC, datetime
from pathlib import Path

from hei_fastapi_ddd.contexts.sys.application.job import cron as cron_util
from hei_fastapi_ddd.contexts.sys.application.job.registry import resolve
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.job_po import SysJobLog
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.job_repository import (
    JobLogRepository,
    JobRepository,
)
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.persistence.session import get_session_factory
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.redis.keys import job_run_lock_key
from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.shared.schema.datetime import ensure_utc_datetime

logger = logging.getLogger(__name__)

# 同一任务执行锁过期时间：覆盖全程，进程崩溃后自动过期放行（对齐 hei-boot @Lock4j）。
LOCK_EXPIRE_SECONDS = 30 * 60
# 获取锁超时后跳过本轮，下个扫描周期重试。
LOCK_ACQUIRE_TIMEOUT_SECONDS = 1
# 调度触发的执行人标识（对齐 hei-boot EXECUTOR_SYSTEM）。
EXECUTOR_SYSTEM = "system"
# sys_job.last_result 最大长度（对齐 varchar(500)）。
MAX_RESULT_LENGTH = 500


def _resolve_instance_ip() -> str:
    """解析本机 IP；失败时回退 127.0.0.1。"""
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


# 执行实例元数据（模块加载时静态解析，对齐 hei-boot 类加载语义）。
INSTANCE_IP = _resolve_instance_ip()
INSTANCE_PROCESS_ID = str(os.getpid())
INSTANCE_APP_DIR = str(Path.cwd())

# 最大并发执行数信号量（对齐 hei-boot jobTaskExecutor 线程池 pool-size）。
_concurrency_semaphore = asyncio.Semaphore(max(1, settings.job.pool_size))
# 持有已提交后台任务引用，避免执行前被垃圾回收。
_running_tasks: set[asyncio.Task] = set()


async def submit_run(job_id: str, *, force: bool, executor: str) -> None:
    """有界并发提交任务执行（信号量内运行），立即返回，不等待执行结果。"""
    task = asyncio.create_task(_execute_with_slot(job_id, force=force, executor=executor))
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)


async def _execute_with_slot(job_id: str, *, force: bool, executor: str) -> None:
    """在并发信号量内执行任务，异常仅记录避免后台任务静默消亡。"""
    async with _concurrency_semaphore:
        try:
            await run_job(job_id, force=force, executor=executor)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Job %s execution task failed", job_id)


async def run_job(job_id: str, *, force: bool, executor: str) -> None:
    """执行单个任务：Redis 锁串行化 → 锁内重查 → 执行 → 更新状态并写日志。"""
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
    """获取互斥锁，超时未获则返回 False（下周期重试）。"""
    deadline = time.monotonic() + LOCK_ACQUIRE_TIMEOUT_SECONDS
    while True:
        acquired = await redis.set(lock_key, "1", nx=True, ex=LOCK_EXPIRE_SECONDS)
        if acquired:
            return True
        if time.monotonic() >= deadline:
            return False
        await asyncio.sleep(0.1)


async def _run_locked(job_id: str, *, force: bool, executor: str) -> None:
    """锁内执行：二次校验任务存在性/启用状态/到期时间后运行处理器。"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        job = await JobRepository(session).get_by_id(job_id)
        if job is None or not job.enabled:
            return
        now = datetime.now(UTC)
        if not force and ensure_utc_datetime(job.next_run_time) > now:
            return

        handler = resolve(job.handler)
        started_at = datetime.now(UTC)
        if handler is None:
            await _record_run(
                session,
                job,
                executor=executor,
                success=False,
                result=f"执行失败: 未找到任务处理器: {job.handler}",
                started_at=started_at,
                duration_ms=0,
            )
            return

        param = dict(job.params) if job.params else None
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
    job,
    *,
    executor: str,
    success: bool,
    result: str,
    started_at: datetime,
    duration_ms: int,
) -> None:
    """事务内原子更新任务执行状态（下次执行时间/结果）并写入执行日志。"""
    next_run_time = cron_util.compute_next_run_time(
        job.trigger_type, job.trigger_config, started_at
    )
    async with transactional(session):
        job.last_run_time = started_at
        job.next_run_time = next_run_time
        job.last_result = (result or "")[:MAX_RESULT_LENGTH] or None
        await JobLogRepository(session).create(
            SysJobLog(
                job_id=job.id,
                params=job.params,
                started_at=started_at,
                duration_ms=duration_ms,
                success=success,
                result=result,
                executor=executor,
                ip=INSTANCE_IP,
                process_id=INSTANCE_PROCESS_ID,
                app_dir=INSTANCE_APP_DIR,
            )
        )
    await session.commit()
