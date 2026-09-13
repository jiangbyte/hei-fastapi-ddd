""" Author: Charlie

操作审计队列：在内存队列中异步消费审计事件，队列溢出时溢出到 DB outbox 或 Redis。

审计事件经事件总线分发，各模块订阅处理；同时提供停机排空与持久化兜底。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass

import orjson

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.messaging import emit

logger = logging.getLogger(__name__)

# 队列溢出且 DB outbox 不可用时的 Redis 兜底列表键。
_REDIS_SPILL_KEY = "audit:operation:spill"

# DB outbox 处理回调：由应用侧装配时注册（core 不依赖业务包）。
_enqueue_outbox_handler: Callable[[OperationAuditEvent], Awaitable[None]] | None = None
_claim_outbox_handler: (
    Callable[[int], Awaitable[list[tuple[OperationAuditEvent, Callable[[], Awaitable[None]]]]]]
    | None
) = None


def register_outbox_handlers(
    enqueue: Callable[[OperationAuditEvent], Awaitable[None]],
    claim: Callable[
        [int],
        Awaitable[list[tuple[OperationAuditEvent, Callable[[], Awaitable[None]]]]],
    ],
) -> None:
    """注册审计 DB outbox 的入队与认领回调。"""
    global _enqueue_outbox_handler, _claim_outbox_handler
    _enqueue_outbox_handler = enqueue
    _claim_outbox_handler = claim


@dataclass(frozen=True, slots=True)
class OperationAuditEvent:
    """操作审计事件载荷：请求资源、动作、来源账户与网络信息。"""

    resource_type: str
    action: str
    method: str
    path: str
    status_code: int
    account_id: str | None
    account_type: str | None
    request_id: str | None
    ip: str | None
    user_agent: str | None
    resource_id: str | None = None
    duration_ms: int | None = None
    summary: str | None = None
    subject: str | None = None
    operator_name: str | None = None
    before_data: dict | None = None
    after_data: dict | None = None
    success: bool = True
    error_message: str | None = None


class OperationAuditQueue:
    """基于 asyncio.Queue 的审计事件消费者，含持久化溢出与停机排空。"""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[OperationAuditEvent] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._spill_worker: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """幂等启动队列：创建写入 worker 与溢出回填 worker。"""
        async with self._lock:
            if self._worker and not self._worker.done():
                return
            self._queue = asyncio.Queue(maxsize=settings.audit.operation_queue_size)
            self._worker = asyncio.create_task(self._run(), name="operation-audit-writer")
            self._spill_worker = asyncio.create_task(
                self._drain_spill(), name="operation-audit-spill"
            )

    async def stop(self) -> None:
        """停止队列：先取消溢出回填，再限时排空队列并取消写入 worker。"""
        async with self._lock:
            queue = self._queue
            worker = self._worker
            spill = self._spill_worker
            self._queue = None
            self._worker = None
            self._spill_worker = None
        if spill is not None:
            spill.cancel()
            try:
                await spill
            except asyncio.CancelledError:
                pass
        if queue is None or worker is None:
            return

        try:
            await asyncio.wait_for(
                queue.join(),
                timeout=settings.audit.operation_shutdown_timeout_seconds,
            )
        except TimeoutError:
            logger.warning("Timed out waiting for operation audit queue to drain")

        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass

    def enqueue(self, event: OperationAuditEvent) -> bool:
        """入队事件；队列未启动或已满时返回 False 并尝试溢出。"""
        queue = self._queue
        if queue is None:
            logger.debug("Operation audit queue is not started; dropping event")
            return False
        try:
            queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            logger.warning("Operation audit queue is full; spilling to durable outbox")
            try:
                asyncio.get_running_loop().create_task(self._spill_durable(event))
            except RuntimeError:
                pass
            return False

    async def _spill_durable(self, event: OperationAuditEvent) -> None:
        """优先写入 DB outbox；DB 失败时回退到 Redis 列表。"""
        if await _write_outbox(event):
            return
        from hei_fastapi_ddd.shared.redis.redis import get_redis

        redis = get_redis()
        if redis is None:
            logger.warning("Audit spill failed: outbox and Redis unavailable")
            return
        try:
            await redis.rpush(_REDIS_SPILL_KEY, orjson.dumps(asdict(event)))
            await redis.ltrim(_REDIS_SPILL_KEY, -10000, -1)
        except Exception:
            logger.warning("Failed to spill audit event to Redis", exc_info=True)

    async def _drain_spill(self) -> None:
        """周期性地把 DB outbox 与 Redis 溢出事件回填到内存队列。"""
        from hei_fastapi_ddd.shared.redis.redis import get_redis

        while True:
            try:
                await asyncio.sleep(2)
                queue = self._queue
                if queue is None:
                    continue
                await _drain_outbox_into(queue)
                redis = get_redis()
                if redis is None:
                    continue
                while True:
                    raw = await redis.lpop(_REDIS_SPILL_KEY)
                    if not raw:
                        break
                    try:
                        data = orjson.loads(raw)
                        event = OperationAuditEvent(**data)
                        await queue.put(event)
                    except Exception:
                        logger.warning("Invalid spilled audit payload", exc_info=True)
                        break
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug("Audit spill drain error", exc_info=True)

    async def _run(self) -> None:
        """队列写入循环：逐条消费并持久化，完成后标记 task_done。"""
        queue = self._queue
        if queue is None:
            return
        while True:
            event = await queue.get()
            try:
                await _record_operation_audit(event)
            except Exception:
                logger.exception("Failed to write operation audit log")
            finally:
                queue.task_done()


async def _record_operation_audit(event: OperationAuditEvent) -> None:
    """持久化审计事件 — 通过事件总线分发，模块自行订阅处理。"""
    await emit("on_audit_event", event=event)


async def _write_outbox(event: OperationAuditEvent) -> bool:
    """尝试写入 DB outbox；失败时返回 False 交由 Redis 兜底。"""
    if _enqueue_outbox_handler is None:
        return False
    try:
        await _enqueue_outbox_handler(event)
        return True
    except Exception:
        logger.warning("Failed to write audit outbox", exc_info=True)
        return False


async def _drain_outbox_into(queue: asyncio.Queue[OperationAuditEvent]) -> None:
    """认领待处理的 outbox 事件并重新入队，成功后标记完成。"""
    if _claim_outbox_handler is None:
        return
    try:
        events = await _claim_outbox_handler(limit=50)
        for event, mark_done in events:
            try:
                await queue.put(event)
                await mark_done()
            except Exception:
                logger.warning("Failed to re-queue outbox audit event", exc_info=True)
                break
    except Exception:
        logger.debug("Audit outbox drain error", exc_info=True)


# 进程级全局审计队列单例。
operation_audit_queue = OperationAuditQueue()


async def start_operation_audit_queue() -> None:
    """启动全局操作审计队列。"""
    await operation_audit_queue.start()


async def stop_operation_audit_queue() -> None:
    """停止全局操作审计队列。"""
    await operation_audit_queue.stop()
