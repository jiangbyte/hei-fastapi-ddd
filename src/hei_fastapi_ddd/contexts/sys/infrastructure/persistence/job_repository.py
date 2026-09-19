"""定时任务仓储实现。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import Select, delete, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.job_po import SysJob, SysJobLog
from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.types.business import NotFoundError


def _job_row(entity: SysJob) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


def _log_row(entity: SysJobLog) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class JobRepositoryImpl:
    """任务定义仓储实现。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Mapping[str, Any], *, next_run_time: datetime) -> dict[str, Any]:
        payload = dict(data)
        payload["next_run_time"] = next_run_time
        entity = SysJob(**payload)
        self.db.add(entity)
        await self.db.flush()
        return _job_row(entity)

    async def _get_po(self, job_id: str) -> SysJob | None:
        return await self.db.get(SysJob, job_id)

    async def get_by_id(self, job_id: str) -> dict[str, Any] | None:
        entity = await self._get_po(job_id)
        return _job_row(entity) if entity is not None else None

    async def get_required(self, job_id: str) -> dict[str, Any]:
        entity = await self._get_po(job_id)
        if entity is None:
            raise NotFoundError("Job not found")
        return _job_row(entity)

    async def update(self, job_id: str, data: Mapping[str, Any]) -> None:
        entity = await self._get_po(job_id)
        if entity is None:
            raise NotFoundError("Job not found")
        for key, value in data.items():
            if key == "id":
                continue
            setattr(entity, key, value)
        await self.db.flush()

    async def update_run_state(
        self,
        job_id: str,
        *,
        last_run_time: datetime,
        next_run_time: datetime,
        last_result: str | None,
    ) -> None:
        entity = await self._get_po(job_id)
        if entity is None:
            return
        entity.last_run_time = last_run_time
        entity.next_run_time = next_run_time
        entity.last_result = last_result
        await self.db.flush()

    async def set_next_run_time(self, job_id: str, next_run_time: datetime) -> None:
        entity = await self._get_po(job_id)
        if entity is None:
            raise NotFoundError("Job not found")
        entity.next_run_time = next_run_time
        await self.db.flush()

    async def delete_many(self, job_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(job_ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysJob).where(SysJob.id.in_(unique_ids)))

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[SysJob]] = select(SysJob)
        count_stmt = select(func.count(SysJob.id))
        sql_filters = []
        if filters.get("name"):
            sql_filters.append(ci_like(SysJob.name, str(filters["name"])))
        if filters.get("trigger_type"):
            sql_filters.append(SysJob.trigger_type == str(filters["trigger_type"]))
        if filters.get("enabled") is not None:
            sql_filters.append(SysJob.enabled == bool(filters["enabled"]))
        if sql_filters:
            stmt = stmt.where(*sql_filters)
            count_stmt = count_stmt.where(*sql_filters)
        stmt = (
            stmt.order_by(SysJob.sort.asc(), SysJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [_job_row(item) for item in items], total

    async def find_due_jobs(self, now: datetime, *, limit: int) -> list[dict[str, Any]]:
        stmt = (
            select(SysJob)
            .where(SysJob.enabled.is_(True), SysJob.next_run_time <= now)
            .order_by(SysJob.sort.asc(), SysJob.next_run_time.asc())
            .limit(limit)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        return [_job_row(item) for item in items]


class JobLogRepositoryImpl:
    """任务日志仓储实现。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Mapping[str, Any]) -> None:
        self.db.add(SysJobLog(**dict(data)))
        await self.db.flush()

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[SysJobLog]] = select(SysJobLog)
        count_stmt = select(func.count(SysJobLog.id))
        sql_filters = []
        if filters.get("job_id"):
            sql_filters.append(SysJobLog.job_id == str(filters["job_id"]))
        if filters.get("success") is not None:
            sql_filters.append(SysJobLog.success == bool(filters["success"]))
        if sql_filters:
            stmt = stmt.where(*sql_filters)
            count_stmt = count_stmt.where(*sql_filters)
        stmt = stmt.order_by(SysJobLog.started_at.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [_log_row(item) for item in items], total

    async def cleanup_expired(self, *, before: datetime, batch_size: int) -> int:
        limit = max(1, batch_size)
        total_deleted = 0
        for _ in range(1000):
            ids_stmt = (
                select(SysJobLog.id)
                .where(SysJobLog.started_at < before)
                .order_by(SysJobLog.started_at.asc())
                .limit(limit)
            )
            ids = list((await self.db.execute(ids_stmt)).scalars().all())
            if not ids:
                break
            result = await self.db.execute(delete(SysJobLog).where(SysJobLog.id.in_(ids)))
            deleted = int(result.rowcount or 0)
            total_deleted += deleted
            await self.db.flush()
            if deleted < limit:
                break
        return total_deleted
