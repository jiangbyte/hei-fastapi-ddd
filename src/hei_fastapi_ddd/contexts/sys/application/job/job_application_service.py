""" Author: Charlie

定时任务服务层：任务维护、启停、立即执行与执行日志分页。
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, to_schema, to_schema_list
from hei_fastapi_ddd.contexts.sys.application.job import cron as cron_util
from hei_fastapi_ddd.contexts.sys.application.job import registry as job_registry
from hei_fastapi_ddd.contexts.sys.application.job.execution import EXECUTOR_SYSTEM, submit_run
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.job_repository import JobLogRepository, JobRepository
from hei_fastapi_ddd.contexts.sys.interfaces.http.job_schemas import (
    JobAdminPageQuery,
    JobCreateRequest,
    JobEnabledRequest,
    JobLogAdminPageQuery,
    JobUpdateRequest,
    SysJobLogSchema,
    SysJobSchema,
)


class JobService:
    """定时任务服务，负责任务维护与执行入口。"""

    def __init__(self, db: AsyncSession):
        """绑定会话并初始化仓储。"""
        self.db = db
        self.repo = JobRepository(db)
        self.log_repo = JobLogRepository(db)

    @staticmethod
    def _ensure_handler(handler: str) -> None:
        """校验 handler 已注册为处理器。"""
        if job_registry.resolve(handler) is None:
            raise BusinessError(f"未找到任务处理器: {handler}")

    async def create(self, payload: JobCreateRequest) -> None:
        """事务内创建任务：校验触发配置并计算首次下次执行时间。"""
        cron_util.validate(payload.trigger_type, payload.trigger_config)
        self._ensure_handler(payload.handler)
        next_run_time = cron_util.compute_next_run_time(
            payload.trigger_type, payload.trigger_config, datetime.now(UTC)
        )
        async with transactional(self.db):
            entity = await self.repo.create(payload, next_run_time=next_run_time)
            audit_snapshots.created_entity(entity)

    async def update(self, payload: JobUpdateRequest) -> None:
        """事务内更新任务：触发类型或配置变更时重置下次执行时间（对齐 hei-boot）。"""
        entity = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(entity)
        async with transactional(self.db):
            config_changed = (
                entity.trigger_type != str(payload.trigger_type)
                or entity.trigger_config != str(payload.trigger_config)
            )
            cron_util.validate(payload.trigger_type, payload.trigger_config)
            self._ensure_handler(payload.handler)
            await self.repo.update(payload)
            if config_changed:
                entity.next_run_time = cron_util.compute_next_run_time(
                    payload.trigger_type, payload.trigger_config, datetime.now(UTC)
                )
            await self.db.flush()
            audit_snapshots.after_entity(entity)

    async def delete(self, payload: IdsRequest) -> None:
        """事务内批量删除任务。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = [
            entity
            for entity_id in unique_ids
            if (entity := await self.repo.get_by_id(entity_id)) is not None
        ]
        async with transactional(self.db):
            audit_snapshots.deleted_all(entities)
            await self.repo.delete_many(unique_ids)

    async def detail(self, query: IdQuery) -> SysJobSchema:
        """查询任务详情并填充审计人昵称。"""
        entity = await self.repo.get_required(query.id)
        schema = to_schema(SysJobSchema, entity)
        return schema

    async def page_admin(self, query: JobAdminPageQuery) -> PageData[SysJobSchema]:
        """管理端分页查询任务并填充审计人昵称。"""
        entities, total = await self.repo.page_admin(query)
        schemas = to_schema_list(SysJobSchema, entities)
        return build_page(query, total, schemas)

    async def update_enabled(self, payload: JobEnabledRequest) -> None:
        """启停任务：重新启用时按当前时间重置下次执行时间，避免立即触发过期任务。"""
        entity = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(entity)
        async with transactional(self.db):
            entity.enabled = bool(payload.enabled)
            if entity.enabled:
                entity.next_run_time = cron_util.compute_next_run_time(
                    entity.trigger_type, entity.trigger_config, datetime.now(UTC)
                )
            await self.db.flush()
            audit_snapshots.after_entity(entity)

    async def run_now(self, payload: IdQuery, *, executor: str | None) -> None:
        """立即执行：校验任务存在且已启用后异步提交（force=true），接口立即返回。"""
        job = await self.repo.get_required(payload.id)
        if not job.enabled:
            raise BusinessError("任务未启用，请先启用后再执行")
        await submit_run(job.id, force=True, executor=executor or EXECUTOR_SYSTEM)

    async def page_logs(self, query: JobLogAdminPageQuery) -> PageData[SysJobLogSchema]:
        """执行日志分页查询。"""
        items, total = await self.log_repo.page_admin(query)
        return build_page(query, total, to_schema_list(SysJobLogSchema, items))
