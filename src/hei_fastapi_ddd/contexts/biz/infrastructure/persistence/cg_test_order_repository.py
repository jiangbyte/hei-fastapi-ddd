"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:54
"""

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from hei_fastapi_ddd.shared.persistence.batch import chunked
from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_order_po import (
    CgTestOrder,
    CgTestOrderItem,
)
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_order_schemas import (
    CgTestOrderAdminPageQuery,
    CgTestOrderCreateRequest,
    CgTestOrderItemAdminPageQuery,
    CgTestOrderItemCreateRequest,
    CgTestOrderItemUpdateRequest,
    CgTestOrderUpdateRequest,
)


class CgTestOrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        payload: CgTestOrderCreateRequest,
        *,
        owner_dept_id: str | None = None,
    ) -> CgTestOrder:
        entity = CgTestOrder(**payload.model_dump())
        if owner_dept_id is not None:
            entity.owner_dept_id = owner_dept_id
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id(self, entity_id: str) -> CgTestOrder | None:
        return await self.db.get(CgTestOrder, entity_id)

    async def get_required(self, entity_id: str) -> CgTestOrder:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestOrder not found")
        return entity

    async def update(self, payload: CgTestOrderUpdateRequest) -> None:
        entity = await self.get_required(payload.id)
        for key, value in payload.model_dump(exclude={"id"}).items():
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
                raise NotFoundError('CgTestOrder not found')
            await self.db.execute(delete(CgTestOrder).where(CgTestOrder.id.in_(batch)))

    async def page_admin(
        self,
        query: CgTestOrderAdminPageQuery,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> tuple[list[CgTestOrder], int]:
        stmt: Select[tuple[CgTestOrder]] = select(CgTestOrder)
        count_stmt = select(func.count(CgTestOrder.id))
        filters = []
        if query.order_no:
            filters.append(ci_like(CgTestOrder.order_no, query.order_no))
        if query.name:
            filters.append(ci_like(CgTestOrder.name, query.name))
        if query.customer_name:
            filters.append(ci_like(CgTestOrder.customer_name, query.customer_name))
        if query.status is not None:
            filters.append(CgTestOrder.status == query.status)
        if query.type:
            filters.append(ci_like(CgTestOrder.type, query.type))
        if data_scope_filter is not None:
            filters.append(data_scope_filter)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = stmt.order_by(CgTestOrder.created_at.desc()).offset(query.offset).limit(query.size)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total


class CgTestOrderItemRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: CgTestOrderItemCreateRequest) -> CgTestOrderItem:
        entity = CgTestOrderItem(**payload.model_dump())
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id(self, entity_id: str) -> CgTestOrderItem | None:
        return await self.db.get(CgTestOrderItem, entity_id)

    async def get_required(self, entity_id: str) -> CgTestOrderItem:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestOrderItem not found")
        return entity

    async def update(self, payload: CgTestOrderItemUpdateRequest) -> None:
        entity = await self.get_required(payload.id)
        for key, value in payload.model_dump(exclude={"id"}).items():
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
                raise NotFoundError('CgTestOrderItem not found')
            await self.db.execute(delete(CgTestOrderItem).where(CgTestOrderItem.id.in_(batch)))

    async def page_admin(self, query: CgTestOrderItemAdminPageQuery) -> tuple[list[CgTestOrderItem], int]:
        stmt: Select[tuple[CgTestOrderItem]] = select(CgTestOrderItem)
        count_stmt = select(func.count(CgTestOrderItem.id))
        filters = []
        if query.order_id:
            filters.append(CgTestOrderItem.order_id == query.order_id)
        if query.name:
            filters.append(ci_like(CgTestOrderItem.name, query.name))
        if query.sku_code:
            filters.append(ci_like(CgTestOrderItem.sku_code, query.sku_code))
        if query.status is not None:
            filters.append(CgTestOrderItem.status == query.status)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = stmt.order_by(CgTestOrderItem.created_at.desc()).offset(query.offset).limit(query.size)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total
