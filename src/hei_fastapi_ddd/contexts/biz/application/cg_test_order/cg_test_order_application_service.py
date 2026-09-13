"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:54
"""

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_order_po import CgTestOrder
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_order_repository import (
    CgTestOrderItemRepository,
    CgTestOrderRepository,
)
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_order_schemas import (
    CgTestOrderAdminPageQuery,
    CgTestOrderCreateRequest,
    CgTestOrderItemAdminPageQuery,
    CgTestOrderItemCreateRequest,
    CgTestOrderItemSchema,
    CgTestOrderItemUpdateRequest,
    CgTestOrderSchema,
    CgTestOrderUpdateRequest,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import (
    IdQuery,
    IdsRequest,
    to_schema,
    to_schema_list,
)
from hei_fastapi_ddd.shared.security.data_scope import (
    build_data_scope_filter,
    default_owner_dept_id,
)
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page


class CgTestOrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CgTestOrderRepository(db)

    async def create(
        self,
        payload: CgTestOrderCreateRequest,
        session: SessionPayload | None = None,
    ) -> None:
        async with transactional(self.db):
            entity = await self.repo.create(
                payload, owner_dept_id=default_owner_dept_id(session)
            )
        audit_snapshots.created_entity(entity)

    async def update(self, payload: CgTestOrderUpdateRequest) -> None:
        existing = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
            updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest) -> None:
        unique_ids = list(dict.fromkeys(payload.ids))
        if not unique_ids:
            return
        entities = [await self.repo.get_required(entity_id) for entity_id in unique_ids]
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(unique_ids)

    async def detail(self, query: IdQuery) -> CgTestOrderSchema:
        schema = to_schema(CgTestOrderSchema, await self.repo.get_required(query.id))
        return schema

    async def page_admin(
        self,
        query: CgTestOrderAdminPageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[CgTestOrderSchema]:
        data_scope_filter = None
        if session is not None:
            data_scope_filter = await build_data_scope_filter(
                self.db,
                session,
                "biz:cgtestorder:page",
                owner_column=CgTestOrder.created_by,
                dept_column=getattr(CgTestOrder, "owner_dept_id", None),
            )
        items, total = await self.repo.page_admin(query, data_scope_filter)
        records = to_schema_list(CgTestOrderSchema, items)
        return build_page(query, total, records)


class CgTestOrderItemService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CgTestOrderItemRepository(db)

    async def create(self, payload: CgTestOrderItemCreateRequest) -> None:
        async with transactional(self.db):
            entity = await self.repo.create(payload)
        audit_snapshots.created_entity(entity)

    async def update(self, payload: CgTestOrderItemUpdateRequest) -> None:
        existing = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
            updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest) -> None:
        unique_ids = list(dict.fromkeys(payload.ids))
        if not unique_ids:
            return
        entities = [await self.repo.get_required(entity_id) for entity_id in unique_ids]
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(unique_ids)

    async def detail(self, query: IdQuery) -> CgTestOrderItemSchema:
        schema = to_schema(CgTestOrderItemSchema, await self.repo.get_required(query.id))
        return schema

    async def page_admin(self, query: CgTestOrderItemAdminPageQuery) -> PageData[CgTestOrderItemSchema]:
        items, total = await self.repo.page_admin(query)
        records = to_schema_list(CgTestOrderItemSchema, items)
        return build_page(query, total, records)
