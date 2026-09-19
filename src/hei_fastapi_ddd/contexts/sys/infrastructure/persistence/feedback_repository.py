"""反馈仓储层：封装 SysFeedback 的增删改查与分页查询。"""

from collections.abc import Mapping
from typing import Any

from sqlalchemy import Select, delete, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.domain.feedback.enums import FeedbackStatus
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.feedback_po import SysFeedback
from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.types.business import NotFoundError


def _row(entity: SysFeedback) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class SysFeedbackRepositoryImpl:
    """反馈数据仓储。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """创建反馈记录，初始状态设为待处理。"""
        payload = dict(data)
        payload.setdefault("status", FeedbackStatus.PENDING.value)
        entity = SysFeedback(**payload)
        self.db.add(entity)
        await self.db.flush()
        return _row(entity)

    async def get_by_id(self, entity_id: str) -> dict[str, Any] | None:
        entity = await self.db.get(SysFeedback, entity_id)
        return _row(entity) if entity is not None else None

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("SysFeedback not found")
        return entity

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None:
        po = await self.db.get(SysFeedback, entity_id)
        if po is None:
            raise NotFoundError("SysFeedback not found")
        for key, value in data.items():
            setattr(po, key, value)
        await self.db.flush()

    async def delete_many(self, entity_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(entity_ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysFeedback).where(SysFeedback.id.in_(unique_ids)))

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[SysFeedback]] = select(SysFeedback)
        count_stmt = select(func.count(SysFeedback.id))
        clauses = []
        title = filters.get("title")
        if title:
            clauses.append(ci_like(SysFeedback.title, str(title)))
        if filters.get("category"):
            clauses.append(SysFeedback.category == filters["category"])
        if filters.get("status"):
            clauses.append(SysFeedback.status == filters["status"])
        if filters.get("submitter_account_type"):
            clauses.append(
                SysFeedback.submitter_account_type == filters["submitter_account_type"]
            )
        if clauses:
            stmt = stmt.where(*clauses)
            count_stmt = count_stmt.where(*clauses)
        stmt = stmt.order_by(SysFeedback.id.desc()).offset(offset).limit(limit)
        items = [_row(e) for e in (await self.db.execute(stmt)).scalars().all()]
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def page_my(
        self,
        filters: Mapping[str, Any],
        *,
        account_type: str,
        account_id: str,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        stmt = select(SysFeedback).where(
            SysFeedback.submitter_account_type == account_type,
            SysFeedback.submitter_account_id == account_id,
        )
        count_stmt = select(func.count(SysFeedback.id)).where(
            SysFeedback.submitter_account_type == account_type,
            SysFeedback.submitter_account_id == account_id,
        )
        clauses = []
        if filters.get("category"):
            clauses.append(SysFeedback.category == filters["category"])
        if filters.get("status"):
            clauses.append(SysFeedback.status == filters["status"])
        if clauses:
            stmt = stmt.where(*clauses)
            count_stmt = count_stmt.where(*clauses)
        stmt = stmt.order_by(SysFeedback.id.desc()).offset(offset).limit(limit)
        items = [_row(e) for e in (await self.db.execute(stmt)).scalars().all()]
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total
