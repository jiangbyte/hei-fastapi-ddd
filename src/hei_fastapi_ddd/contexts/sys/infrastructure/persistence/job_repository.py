""" Author: Charlie

定时任务仓储层：封装 sys_job / sys_job_log 持久化、分页与到期扫描。
"""

from datetime import datetime

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.job_po import SysJob, SysJobLog
from hei_fastapi_ddd.contexts.sys.interfaces.http.job_schemas import JobAdminPageQuery, JobCreateRequest, JobLogAdminPageQuery


class JobRepository:
    """任务定义仓储。"""

    def __init__(self, db: AsyncSession):
        """绑定数据库会话。"""
        self.db = db

    async def create(self, payload: JobCreateRequest, *, next_run_time: datetime) -> SysJob:
        """新增任务并 flush（首次下次执行时间由服务层计算）。"""
        entity = SysJob(**payload.model_dump(), next_run_time=next_run_time)
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id(self, job_id: str) -> SysJob | None:
        """按主键查询任务，不存在返回 None。"""
        return await self.db.get(SysJob, job_id)

    async def get_required(self, job_id: str) -> SysJob:
        """按主键查询任务，不存在时抛出 NotFoundError。"""
        entity = await self.get_by_id(job_id)
        if entity is None:
            raise NotFoundError("Job not found")
        return entity

    async def update(self, payload) -> None:
        """按主键更新任务字段（排除 id）。"""
        entity = await self.get_required(payload.id)
        data = payload.model_dump(exclude={"id"})
        for key, value in data.items():
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, job_ids: list[str]) -> None:
        """批量删除任务（不存在的 ID 静默跳过，对齐 hei-boot 幂等语义）。"""
        unique_ids = list(dict.fromkeys(job_ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysJob).where(SysJob.id.in_(unique_ids)))

    async def page_admin(self, query: JobAdminPageQuery) -> tuple[list[SysJob], int]:
        """按查询条件后台分页，返回任务列表与总数。"""
        stmt: Select[tuple[SysJob]] = select(SysJob)
        count_stmt = select(func.count(SysJob.id))
        filters = []
        if query.name:
            filters.append(ci_like(SysJob.name, query.name))
        if query.trigger_type:
            filters.append(SysJob.trigger_type == str(query.trigger_type))
        if query.enabled is not None:
            filters.append(SysJob.enabled == bool(query.enabled))
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysJob.sort.asc(), SysJob.created_at.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def find_due_jobs(self, now: datetime, *, limit: int) -> list[SysJob]:
        """查询已启用且到期（next_run_time <= now）的任务，按 sort、next_run_time 排序。"""
        stmt = (
            select(SysJob)
            .where(SysJob.enabled.is_(True), SysJob.next_run_time <= now)
            .order_by(SysJob.sort.asc(), SysJob.next_run_time.asc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())


class JobLogRepository:
    """任务执行日志仓储。"""

    def __init__(self, db: AsyncSession):
        """绑定数据库会话。"""
        self.db = db

    async def create(self, log: SysJobLog) -> None:
        """写入一条执行日志。"""
        self.db.add(log)
        await self.db.flush()

    async def page_admin(self, query: JobLogAdminPageQuery) -> tuple[list[SysJobLog], int]:
        """按查询条件后台分页，返回日志列表与总数。"""
        stmt: Select[tuple[SysJobLog]] = select(SysJobLog)
        count_stmt = select(func.count(SysJobLog.id))
        filters = []
        if query.job_id:
            filters.append(SysJobLog.job_id == str(query.job_id))
        if query.success is not None:
            filters.append(SysJobLog.success == bool(query.success))
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysJobLog.started_at.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def cleanup_expired(self, *, before: datetime, batch_size: int) -> int:
        """按 started_at 分批删除过期日志，返回累计删除行数。"""
        limit = max(1, batch_size)
        total_deleted = 0
        max_rounds = 1000
        for _ in range(max_rounds):
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
