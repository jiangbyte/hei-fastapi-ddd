"""cg_test_order 应用服务。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.biz.application.cg_test_order.dto import (
    CgTestOrderCreateCommand,
    CgTestOrderItemCreateCommand,
    CgTestOrderItemPageQuery,
    CgTestOrderItemUpdateCommand,
    CgTestOrderPageQuery,
    CgTestOrderUpdateCommand,
)
from hei_fastapi_ddd.contexts.biz.domain.cg_test_order.repository import (
    CgTestOrderItemRepository,
    CgTestOrderRepository,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.security.data_scope import default_owner_dept_id
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page


class CgTestOrderService:
    def __init__(self, db: AsyncSession, repo: CgTestOrderRepository):
        self.db = db
        self.repo = repo

    async def create(
        self, command: CgTestOrderCreateCommand, session: SessionPayload | None = None
    ) -> None:
        async with transactional(self.db):
            entity = await self.repo.create(
                command.model_dump(), owner_dept_id=default_owner_dept_id(session)
            )
        audit_snapshots.created_entity(entity)

    async def update(self, command: CgTestOrderUpdateCommand) -> None:
        existing = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(command.id, command.model_dump(exclude={"id"}))
            updated = await self.repo.get_required(command.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(ids))
        if not unique_ids:
            return
        entities = [await self.repo.get_required(i) for i in unique_ids]
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(unique_ids)

    async def detail(self, entity_id: str) -> dict:
        return await self.repo.get_required(entity_id)

    async def page_admin(
        self, query: CgTestOrderPageQuery, session: SessionPayload | None = None
    ) -> PageData[dict]:
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
            session=session,
        )
        return build_page(query, total, items)  # type: ignore[arg-type]


class CgTestOrderItemService:
    def __init__(self, db: AsyncSession, repo: CgTestOrderItemRepository):
        self.db = db
        self.repo = repo

    async def create(self, command: CgTestOrderItemCreateCommand) -> None:
        async with transactional(self.db):
            entity = await self.repo.create(command.model_dump())
        audit_snapshots.created_entity(entity)

    async def update(self, command: CgTestOrderItemUpdateCommand) -> None:
        existing = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(command.id, command.model_dump(exclude={"id"}))
            updated = await self.repo.get_required(command.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(ids))
        if not unique_ids:
            return
        entities = [await self.repo.get_required(i) for i in unique_ids]
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(unique_ids)

    async def detail(self, entity_id: str) -> dict:
        return await self.repo.get_required(entity_id)

    async def page_admin(self, query: CgTestOrderItemPageQuery) -> PageData[dict]:
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
        )
        return build_page(query, total, items)  # type: ignore[arg-type]
