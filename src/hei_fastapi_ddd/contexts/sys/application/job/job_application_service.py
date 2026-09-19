""" Author: Charlie

定时任务应用服务。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.job import cron as cron_util
from hei_fastapi_ddd.contexts.sys.application.job import registry as job_registry
from hei_fastapi_ddd.contexts.sys.application.job.dto import (
    JobAdminPageQuery,
    JobCreateCommand,
    JobEnabledCommand,
    JobLogAdminPageQuery,
    JobUpdateCommand,
)
from hei_fastapi_ddd.contexts.sys.application.job.execution import EXECUTOR_SYSTEM
from hei_fastapi_ddd.contexts.sys.domain.job.repository import JobLogRepository, JobRepository
from hei_fastapi_ddd.contexts.sys.domain.job.runner import JobRunnerPort
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import BusinessError


class JobService:
    """定时任务服务。"""

    def __init__(
        self,
        db: AsyncSession,
        repo: JobRepository,
        log_repo: JobLogRepository,
        runner: JobRunnerPort,
    ):
        self.db = db
        self.repo = repo
        self.log_repo = log_repo
        self.runner = runner

    @staticmethod
    def _ensure_handler(handler: str) -> None:
        if job_registry.resolve(handler) is None:
            raise BusinessError(f"未找到任务处理器: {handler}")

    async def create(self, command: JobCreateCommand) -> None:
        """事务内创建任务。"""
        cron_util.validate(command.trigger_type, command.trigger_config)
        self._ensure_handler(command.handler)
        next_run_time = cron_util.compute_next_run_time(
            command.trigger_type, command.trigger_config, datetime.now(UTC)
        )
        async with transactional(self.db):
            row = await self.repo.create(command.model_dump(), next_run_time=next_run_time)
            audit_snapshots.created_entity(row)

    async def update(self, command: JobUpdateCommand) -> None:
        """事务内更新任务。"""
        existing = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(existing)
        config_changed = (
            existing.get("trigger_type") != str(command.trigger_type)
            or existing.get("trigger_config") != str(command.trigger_config)
        )
        cron_util.validate(command.trigger_type, command.trigger_config)
        self._ensure_handler(command.handler)
        async with transactional(self.db):
            await self.repo.update(command.id, command.model_dump(exclude={"id"}))
            if config_changed:
                await self.repo.set_next_run_time(
                    command.id,
                    cron_util.compute_next_run_time(
                        command.trigger_type, command.trigger_config, datetime.now(UTC)
                    ),
                )
            updated = await self.repo.get_required(command.id)
            audit_snapshots.after_entity(updated)

    async def delete(self, ids: list[str]) -> None:
        """事务内批量删除任务。"""
        unique_ids = list(dict.fromkeys(ids))
        entities = [
            row
            for entity_id in unique_ids
            if (row := await self.repo.get_by_id(entity_id)) is not None
        ]
        async with transactional(self.db):
            audit_snapshots.deleted_all(entities)
            await self.repo.delete_many(unique_ids)

    async def detail(self, job_id: str) -> dict:
        return await self.repo.get_required(job_id)

    async def page_admin(self, query: JobAdminPageQuery) -> PageData[dict]:
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
        )
        return build_page(query, total, items)  # type: ignore[arg-type]

    async def update_enabled(self, command: JobEnabledCommand) -> None:
        """启停任务。"""
        existing = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            data = {"enabled": bool(command.enabled)}
            if command.enabled:
                data["next_run_time"] = cron_util.compute_next_run_time(
                    str(existing.get("trigger_type")),
                    str(existing.get("trigger_config")),
                    datetime.now(UTC),
                )
            await self.repo.update(command.id, data)
            updated = await self.repo.get_required(command.id)
            audit_snapshots.after_entity(updated)

    async def run_now(self, job_id: str, *, executor: str | None) -> None:
        job = await self.repo.get_required(job_id)
        if not job.get("enabled"):
            raise BusinessError("任务未启用，请先启用后再执行")
        await self.runner.submit(
            str(job["id"]), force=True, executor=executor or EXECUTOR_SYSTEM
        )

    async def cleanup_expired_logs(self, before: datetime, batch_size: int) -> int:
        """清理过期执行日志。"""
        return await self.log_repo.cleanup_expired(before=before, batch_size=batch_size)

    async def page_logs(self, query: JobLogAdminPageQuery) -> PageData[dict]:
        items, total = await self.log_repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
        )
        return build_page(query, total, items)  # type: ignore[arg-type]
