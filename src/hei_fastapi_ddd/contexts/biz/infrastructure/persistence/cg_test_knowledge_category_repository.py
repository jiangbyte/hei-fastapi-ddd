"""知识分类/文档仓储实现。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import Select, delete, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_knowledge_category_po import (
    CgTestKnowledgeCategory,
    CgTestKnowledgeDoc,
)
from hei_fastapi_ddd.shared.persistence.batch import chunked
from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.shared.security.data_scope import build_data_scope_filter
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.types.business import NotFoundError


def _row(entity: object) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class CgTestKnowledgeCategoryRepositoryImpl:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, data: Mapping[str, Any], *, owner_dept_id: str | None = None
    ) -> dict[str, Any]:
        entity = CgTestKnowledgeCategory(**dict(data))
        if owner_dept_id is not None:
            entity.owner_dept_id = owner_dept_id
        self.db.add(entity)
        await self.db.flush()
        return _row(entity)

    async def get_by_id(self, entity_id: str) -> CgTestKnowledgeCategory | None:
        return await self.db.get(CgTestKnowledgeCategory, entity_id)

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestKnowledgeCategory not found")
        return _row(entity)

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestKnowledgeCategory not found")
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
            stmt = select(CgTestKnowledgeCategory.id).where(CgTestKnowledgeCategory.id.in_(batch))
            existing_ids = set((await self.db.execute(stmt)).scalars().all())
            if len(existing_ids) != len(batch):
                raise NotFoundError("CgTestKnowledgeCategory not found")
            await self.db.execute(
                delete(CgTestKnowledgeCategory).where(CgTestKnowledgeCategory.id.in_(batch))
            )

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
        session: SessionPayload | None = None,
        permission: str = "biz:cgtestknowledgecategory:page",
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[CgTestKnowledgeCategory]] = select(CgTestKnowledgeCategory)
        count_stmt = select(func.count(CgTestKnowledgeCategory.id))
        where = []
        if filters.get("code"):
            where.append(ci_like(CgTestKnowledgeCategory.code, filters["code"]))
        if filters.get("name"):
            where.append(ci_like(CgTestKnowledgeCategory.name, filters["name"]))
        if filters.get("status") is not None:
            where.append(CgTestKnowledgeCategory.status == filters["status"])
        if session is not None:
            data_scope_filter = await build_data_scope_filter(
                self.db,
                session,
                permission,
                owner_column=CgTestKnowledgeCategory.created_by,
                dept_column=getattr(CgTestKnowledgeCategory, "owner_dept_id", None),
            )
            if data_scope_filter is not None:
                where.append(data_scope_filter)
        if where:
            stmt = stmt.where(*where)
            count_stmt = count_stmt.where(*where)
        stmt = (
            stmt.order_by(CgTestKnowledgeCategory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [_row(item) for item in items], total

    async def get_parent_name_map(self, parent_ids: set[str]) -> dict[str, str]:
        if not parent_ids:
            return {}
        result: dict[str, str] = {}
        for batch in chunked(sorted(parent_ids)):
            stmt = select(CgTestKnowledgeCategory.id, CgTestKnowledgeCategory.name).where(
                CgTestKnowledgeCategory.id.in_(batch)
            )
            rows = (await self.db.execute(stmt)).all()
            result.update({str(id_): str(name or id_) for id_, name in rows})
        return result

    async def list_tree(
        self,
        keyword: str | None = None,
        *,
        session: SessionPayload | None = None,
        permission: str = "biz:cgtestknowledgecategory:list",
    ) -> list[dict[str, Any]]:
        stmt = select(CgTestKnowledgeCategory).order_by(CgTestKnowledgeCategory.id.asc())
        where = []
        if keyword:
            where.append(ci_like(CgTestKnowledgeCategory.name, keyword))
        if session is not None:
            data_scope_filter = await build_data_scope_filter(
                self.db,
                session,
                permission,
                owner_column=CgTestKnowledgeCategory.created_by,
                dept_column=getattr(CgTestKnowledgeCategory, "owner_dept_id", None),
            )
            if data_scope_filter is not None:
                where.append(data_scope_filter)
        if where:
            stmt = stmt.where(*where)
        return [_row(item) for item in (await self.db.execute(stmt)).scalars().all()]


class CgTestKnowledgeDocRepositoryImpl:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        entity = CgTestKnowledgeDoc(**dict(data))
        self.db.add(entity)
        await self.db.flush()
        return _row(entity)

    async def get_by_id(self, entity_id: str) -> CgTestKnowledgeDoc | None:
        return await self.db.get(CgTestKnowledgeDoc, entity_id)

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestKnowledgeDoc not found")
        return _row(entity)

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestKnowledgeDoc not found")
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
            stmt = select(CgTestKnowledgeDoc.id).where(CgTestKnowledgeDoc.id.in_(batch))
            existing_ids = set((await self.db.execute(stmt)).scalars().all())
            if len(existing_ids) != len(batch):
                raise NotFoundError("CgTestKnowledgeDoc not found")
            await self.db.execute(
                delete(CgTestKnowledgeDoc).where(CgTestKnowledgeDoc.id.in_(batch))
            )

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[CgTestKnowledgeDoc]] = select(CgTestKnowledgeDoc)
        count_stmt = select(func.count(CgTestKnowledgeDoc.id))
        where = []
        if filters.get("category_id"):
            where.append(CgTestKnowledgeDoc.category_id == filters["category_id"])
        if filters.get("code"):
            where.append(ci_like(CgTestKnowledgeDoc.code, filters["code"]))
        if filters.get("title"):
            where.append(ci_like(CgTestKnowledgeDoc.title, filters["title"]))
        if filters.get("type"):
            where.append(ci_like(CgTestKnowledgeDoc.type, filters["type"]))
        if filters.get("status") is not None:
            where.append(CgTestKnowledgeDoc.status == filters["status"])
        if where:
            stmt = stmt.where(*where)
            count_stmt = count_stmt.where(*where)
        stmt = stmt.order_by(CgTestKnowledgeDoc.id.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [_row(item) for item in items], total
