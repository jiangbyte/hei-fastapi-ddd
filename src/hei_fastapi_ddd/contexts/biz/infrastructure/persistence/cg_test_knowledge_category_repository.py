"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:55
"""

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from hei_fastapi_ddd.shared.persistence.batch import chunked
from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_knowledge_category_po import (
    CgTestKnowledgeCategory,
    CgTestKnowledgeDoc,
)
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_knowledge_category_schemas import (
    CgTestKnowledgeCategoryAdminPageQuery,
    CgTestKnowledgeCategoryCreateRequest,
    CgTestKnowledgeCategoryUpdateRequest,
    CgTestKnowledgeDocAdminPageQuery,
    CgTestKnowledgeDocCreateRequest,
    CgTestKnowledgeDocUpdateRequest,
)


class CgTestKnowledgeCategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        payload: CgTestKnowledgeCategoryCreateRequest,
        *,
        owner_dept_id: str | None = None,
    ) -> CgTestKnowledgeCategory:
        entity = CgTestKnowledgeCategory(**payload.model_dump())
        if owner_dept_id is not None:
            entity.owner_dept_id = owner_dept_id
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id(self, entity_id: str) -> CgTestKnowledgeCategory | None:
        return await self.db.get(CgTestKnowledgeCategory, entity_id)

    async def get_required(self, entity_id: str) -> CgTestKnowledgeCategory:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestKnowledgeCategory not found")
        return entity

    async def update(self, payload: CgTestKnowledgeCategoryUpdateRequest) -> None:
        entity = await self.get_required(payload.id)
        for key, value in payload.model_dump(exclude={"id"}).items():
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
                raise NotFoundError('CgTestKnowledgeCategory not found')
            await self.db.execute(delete(CgTestKnowledgeCategory).where(CgTestKnowledgeCategory.id.in_(batch)))

    async def page_admin(
        self,
        query: CgTestKnowledgeCategoryAdminPageQuery,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> tuple[list[CgTestKnowledgeCategory], int]:
        stmt: Select[tuple[CgTestKnowledgeCategory]] = select(CgTestKnowledgeCategory)
        count_stmt = select(func.count(CgTestKnowledgeCategory.id))
        filters = []
        if query.code:
            filters.append(ci_like(CgTestKnowledgeCategory.code, query.code))
        if query.name:
            filters.append(ci_like(CgTestKnowledgeCategory.name, query.name))
        if query.status is not None:
            filters.append(CgTestKnowledgeCategory.status == query.status)
        if data_scope_filter is not None:
            filters.append(data_scope_filter)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = stmt.order_by(CgTestKnowledgeCategory.created_at.desc()).offset(query.offset).limit(query.size)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def get_parent_name_map(self, parent_ids: set[str]) -> dict[str, str]:
        if not parent_ids:
            return {}
        result: dict[str, str] = {}
        for batch in chunked(sorted(parent_ids)):
            stmt = select(CgTestKnowledgeCategory.id, CgTestKnowledgeCategory.name).where(CgTestKnowledgeCategory.id.in_(batch))
            rows = (await self.db.execute(stmt)).all()
            result.update({str(id_): str(name or id_) for id_, name in rows})
        return result

    async def list_tree(
        self,
        keyword: str | None = None,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> list[CgTestKnowledgeCategory]:
        stmt = select(CgTestKnowledgeCategory).order_by(CgTestKnowledgeCategory.id.asc())
        filters = []
        if keyword:
            filters.append(ci_like(CgTestKnowledgeCategory.name, keyword))
        if data_scope_filter is not None:
            filters.append(data_scope_filter)
        if filters:
            stmt = stmt.where(*filters)
        return list((await self.db.execute(stmt)).scalars().all())


class CgTestKnowledgeDocRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: CgTestKnowledgeDocCreateRequest) -> CgTestKnowledgeDoc:
        entity = CgTestKnowledgeDoc(**payload.model_dump())
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id(self, entity_id: str) -> CgTestKnowledgeDoc | None:
        return await self.db.get(CgTestKnowledgeDoc, entity_id)

    async def get_required(self, entity_id: str) -> CgTestKnowledgeDoc:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestKnowledgeDoc not found")
        return entity

    async def update(self, payload: CgTestKnowledgeDocUpdateRequest) -> None:
        entity = await self.get_required(payload.id)
        for key, value in payload.model_dump(exclude={"id"}).items():
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
                raise NotFoundError('CgTestKnowledgeDoc not found')
            await self.db.execute(delete(CgTestKnowledgeDoc).where(CgTestKnowledgeDoc.id.in_(batch)))

    async def page_admin(self, query: CgTestKnowledgeDocAdminPageQuery) -> tuple[list[CgTestKnowledgeDoc], int]:
        stmt: Select[tuple[CgTestKnowledgeDoc]] = select(CgTestKnowledgeDoc)
        count_stmt = select(func.count(CgTestKnowledgeDoc.id))
        filters = []
        if query.category_id:
            filters.append(CgTestKnowledgeDoc.category_id == query.category_id)
        if query.code:
            filters.append(ci_like(CgTestKnowledgeDoc.code, query.code))
        if query.title:
            filters.append(ci_like(CgTestKnowledgeDoc.title, query.title))
        if query.type:
            filters.append(ci_like(CgTestKnowledgeDoc.type, query.type))
        if query.status is not None:
            filters.append(CgTestKnowledgeDoc.status == query.status)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = stmt.order_by(CgTestKnowledgeDoc.id.desc()).offset(query.offset).limit(query.size)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total
