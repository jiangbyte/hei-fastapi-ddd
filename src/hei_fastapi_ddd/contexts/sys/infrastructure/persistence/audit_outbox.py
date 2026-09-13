""" Author: Charlie

持久化审计发件箱，用于溢出/崩溃恢复。
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import UTC, datetime

import orjson
from sqlalchemy import DateTime, Integer, String, Text, delete, func, select, update
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.audit.queue import OperationAuditEvent
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.session import get_session_factory
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
class SysOperationAuditOutbox(Base):
    """审计发件箱表：在审计队列溢出或进程崩溃时暂存事件以恢复。"""

    __tablename__ = "sys_operation_audit_outbox"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False, comment="事件 JSON")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        comment="PENDING|CLAIMED|DONE",
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="尝试次数")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="认领时间",
    )


async def enqueue_outbox(event: OperationAuditEvent) -> None:
    """将审计事件序列化后写入发件箱（PENDING），用于溢出/崩溃恢复。"""
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            SysOperationAuditOutbox(
                payload=orjson.dumps(asdict(event)).decode(),
                status="PENDING",
            )
        )
        await session.commit()


async def claim_pending_outbox(
    *,
    limit: int = 50,
) -> list[tuple[OperationAuditEvent, Callable[[], Awaitable[None]]]]:
    """认领一批 PENDING 事件并标记 CLAIMED，返回事件及其完成回调。"""
    factory = get_session_factory()
    claimed: list[tuple[OperationAuditEvent, Callable[[], Awaitable[None]]]] = []
    async with factory() as session:
        rows = list(
            (
                await session.execute(
                    select(SysOperationAuditOutbox)
                    .where(SysOperationAuditOutbox.status == "PENDING")
                    .order_by(SysOperationAuditOutbox.created_at.asc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            return []
        now = datetime.now(UTC)
        for row in rows:
            try:
                data = orjson.loads(row.payload)
                event = OperationAuditEvent(**data)
            except Exception:
                # 载荷损坏或结构不匹配：直接标记 DONE 并计入尝试次数，避免反复重试阻塞队列。
                await session.execute(
                    update(SysOperationAuditOutbox)
                    .where(SysOperationAuditOutbox.id == row.id)
                    .values(status="DONE", attempts=row.attempts + 1, claimed_at=now)
                )
                continue

            row_id = row.id

            async def _mark_done(outbox_id: str = row_id) -> None:
                """成功处理后删除记录，避免发件箱无界增长。"""
                async with factory() as done_session:
                    await done_session.execute(
                        delete(SysOperationAuditOutbox).where(
                            SysOperationAuditOutbox.id == outbox_id
                        )
                    )
                    await done_session.commit()

            await session.execute(
                update(SysOperationAuditOutbox)
                .where(SysOperationAuditOutbox.id == row.id)
                .values(
                    status="CLAIMED",
                    attempts=row.attempts + 1,
                    claimed_at=now,
                )
            )
            claimed.append((event, _mark_done))
        await session.commit()
    return claimed
