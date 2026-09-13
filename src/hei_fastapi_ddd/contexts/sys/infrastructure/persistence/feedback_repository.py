""" Author: Charlie

由 HEI 代码生成器生成。
Author: jiangbyte

反馈仓储层：封装 SysFeedback 的增删改查与分页查询。
"""

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.domain.feedback.enums import FeedbackStatus
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.feedback_po import SysFeedback
from hei_fastapi_ddd.contexts.sys.interfaces.http.feedback_schemas import (
    MyFeedbackPageQuery,
    SysFeedbackAdminPageQuery,
    SysFeedbackCreateRequest,
)
from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.shared.persistence.compat import ci_like


class SysFeedbackRepository:
    """反馈数据仓储，负责 SysFeedback 的持久化与分页查询。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        payload: SysFeedbackCreateRequest,
        *,
        submitter_account_type: str,
        submitter_account_id: str,
        attach_object_names: list[str] | None = None,
    ) -> SysFeedback:
        """创建反馈记录，初始状态设为待处理。"""
        data = payload.model_dump()
        data["attach_object_names"] = (
            attach_object_names
            if attach_object_names is not None
            else data.get("attach_object_names") or []
        )
        entity = SysFeedback(
            **data,
            status=FeedbackStatus.PENDING.value,
            submitter_account_type=submitter_account_type,
            submitter_account_id=submitter_account_id,
        )
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id(self, entity_id: str) -> SysFeedback | None:
        """按主键查询反馈记录，不存在时返回 None。"""
        return await self.db.get(SysFeedback, entity_id)

    async def get_required(self, entity_id: str) -> SysFeedback:
        """按主键查询反馈记录，不存在时抛出 NotFoundError。"""
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("SysFeedback not found")
        return entity

    async def delete_many(self, entity_ids: list[str]) -> None:
        """批量删除反馈（不存在的 ID 静默跳过，对齐 hei-boot 幂等语义）。"""
        unique_ids = list(dict.fromkeys(entity_ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysFeedback).where(SysFeedback.id.in_(unique_ids)))

    async def page_admin(self, query: SysFeedbackAdminPageQuery) -> tuple[list[SysFeedback], int]:
        """管理端分页查询反馈，支持标题/分类/状态/提交者类型过滤。"""
        stmt: Select[tuple[SysFeedback]] = select(SysFeedback)
        count_stmt = select(func.count(SysFeedback.id))
        filters = []
        if query.title:
            filters.append(ci_like(SysFeedback.title, query.title))
        if query.category:
            filters.append(SysFeedback.category == query.category)
        if query.status:
            filters.append(SysFeedback.status == query.status)
        if query.submitter_account_type:
            filters.append(
                SysFeedback.submitter_account_type == query.submitter_account_type
            )
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysFeedback.id.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def page_my(
        self,
        query: MyFeedbackPageQuery,
        account_type: str,
        account_id: str,
    ) -> tuple[list[SysFeedback], int]:
        """按当前提交者账户过滤，分页查询「我的反馈」。"""
        stmt = select(SysFeedback).where(
            SysFeedback.submitter_account_type == account_type,
            SysFeedback.submitter_account_id == account_id,
        )
        count_stmt = select(func.count(SysFeedback.id)).where(
            SysFeedback.submitter_account_type == account_type,
            SysFeedback.submitter_account_id == account_id,
        )
        filters = []
        if query.category:
            filters.append(SysFeedback.category == query.category)
        if query.status:
            filters.append(SysFeedback.status == query.status)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysFeedback.id.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total
