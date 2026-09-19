"""cg_test_order 仓储实现。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import Select, delete, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_order_po import (
    CgTestOrder,
    CgTestOrderItem,
)
from hei_fastapi_ddd.shared.persistence.batch import chunked
from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.shared.security.data_scope import build_data_scope_filter
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.types.business import NotFoundError


def _row(entity: object) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class CgTestOrderRepositoryImpl:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, data: Mapping[str, Any], *, owner_dept_id: str | None = None
    ) -> dict[str, Any]:
        entity = CgTestOrder(**dict(data))
        if owner_dept_id is not None:
            entity.owner_dept_id = owner_dept_id
        self.db.add(entity)
        await self.db.flush()
        return _row(entity)

    async def get_by_id(self, entity_id: str) -> CgTestOrder | None:
        return await self.db.get(CgTestOrder, entity_id)

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestOrder not found")
        return _row(entity)

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestOrder not found")
        for key, value in data.items():
            if key == "id":
                continue
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, entity_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(entity_ids))
        if not unique_ids:
            return
        for batch in chunked(unique_ids):
            stmt = select(CgTestOrder.id).where(CgTestOrder.id.in_(batch))
            existing_ids = set((await self.db.execute(stmt)).scalars().all())
            if len(existing_ids) != len(batch):
                raise NotFoundError("CgTestOrder not found")
            await self.db.execute(delete(CgTestOrder).where(CgTestOrder.id.in_(batch)))

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
        session: SessionPayload | None = None,
        permission: str = "biz:cgtestorder:page",
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[CgTestOrder]] = select(CgTestOrder)
        count_stmt = select(func.count(CgTestOrder.id))
        where = []
        if filters.get("order_no"):
            where.append(ci_like(CgTestOrder.order_no, filters["order_no"]))
        if filters.get("name"):
            where.append(ci_like(CgTestOrder.name, filters["name"]))
        if filters.get("customer_name"):
            where.append(ci_like(CgTestOrder.customer_name, filters["customer_name"]))
        if filters.get("status") is not None:
            where.append(CgTestOrder.status == filters["status"])
        if filters.get("type"):
            where.append(ci_like(CgTestOrder.type, filters["type"]))
        if session is not None:
            data_scope_filter = await build_data_scope_filter(
                self.db,
                session,
                permission,
                owner_column=CgTestOrder.created_by,
                dept_column=getattr(CgTestOrder, "owner_dept_id", None),
            )
            if data_scope_filter is not None:
                where.append(data_scope_filter)
        if where:
            stmt = stmt.where(*where)
            count_stmt = count_stmt.where(*where)
        stmt = stmt.order_by(CgTestOrder.created_at.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [_row(item) for item in items], total


class CgTestOrderItemRepositoryImpl:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        entity = CgTestOrderItem(**dict(data))
        self.db.add(entity)
        await self.db.flush()
        return _row(entity)

    async def get_by_id(self, entity_id: str) -> CgTestOrderItem | None:
        return await self.db.get(CgTestOrderItem, entity_id)

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestOrderItem not found")
        return _row(entity)

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestOrderItem not found")
        for key, value in data.items():
            if key == "id":
                continue
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, entity_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(entity_ids))
        if not unique_ids:
            return
        for batch in chunked(unique_ids):
            stmt = select(CgTestOrderItem.id).where(CgTestOrderItem.id.in_(batch))
            existing_ids = set((await self.db.execute(stmt)).scalars().all())
            if len(existing_ids) != len(batch):
                raise NotFoundError("CgTestOrderItem not found")
            await self.db.execute(delete(CgTestOrderItem).where(CgTestOrderItem.id.in_(batch)))

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[CgTestOrderItem]] = select(CgTestOrderItem)
        count_stmt = select(func.count(CgTestOrderItem.id))
        where = []
        if filters.get("order_id"):
            where.append(CgTestOrderItem.order_id == filters["order_id"])
        if filters.get("name"):
            where.append(ci_like(CgTestOrderItem.name, filters["name"]))
        if filters.get("sku_code"):
            where.append(ci_like(CgTestOrderItem.sku_code, filters["sku_code"]))
        if filters.get("status") is not None:
            where.append(CgTestOrderItem.status == filters["status"])
        if where:
            stmt = stmt.where(*where)
            count_stmt = count_stmt.where(*where)
        stmt = stmt.order_by(CgTestOrderItem.created_at.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [_row(item) for item in items], total
