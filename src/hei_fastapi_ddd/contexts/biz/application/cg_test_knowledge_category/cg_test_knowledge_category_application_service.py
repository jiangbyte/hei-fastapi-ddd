"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:55
"""

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_knowledge_category_po import (
    CgTestKnowledgeCategory,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_knowledge_category_repository import (
    CgTestKnowledgeCategoryRepository,
    CgTestKnowledgeDocRepository,
)
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_knowledge_category_schemas import (
    CgTestKnowledgeCategoryAdminPageQuery,
    CgTestKnowledgeCategoryCreateRequest,
    CgTestKnowledgeCategoryDetailSchema,
    CgTestKnowledgeCategorySchema,
    CgTestKnowledgeCategoryTreeNode,
    CgTestKnowledgeCategoryUpdateRequest,
    CgTestKnowledgeDocAdminPageQuery,
    CgTestKnowledgeDocCreateRequest,
    CgTestKnowledgeDocSchema,
    CgTestKnowledgeDocUpdateRequest,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import (
    IdQuery,
    IdsRequest,
    KeywordQuery,
    to_schema,
    to_schema_list,
)
from hei_fastapi_ddd.shared.security.data_scope import (
    build_data_scope_filter,
    default_owner_dept_id,
)
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page


class CgTestKnowledgeCategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CgTestKnowledgeCategoryRepository(db)

    async def create(
        self,
        payload: CgTestKnowledgeCategoryCreateRequest,
        session: SessionPayload | None = None,
    ) -> None:
        async with transactional(self.db):
            entity = await self.repo.create(
                payload, owner_dept_id=default_owner_dept_id(session)
            )
        audit_snapshots.created_entity(entity)

    async def update(self, payload: CgTestKnowledgeCategoryUpdateRequest) -> None:
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

    async def detail(self, query: IdQuery) -> CgTestKnowledgeCategoryDetailSchema:
        schema = await self._to_schema_with_parent_name(await self.repo.get_required(query.id))
        return schema

    async def page_admin(
        self,
        query: CgTestKnowledgeCategoryAdminPageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[CgTestKnowledgeCategorySchema]:
        data_scope_filter = None
        if session is not None:
            data_scope_filter = await build_data_scope_filter(
                self.db,
                session,
                "biz:cgtestknowledgecategory:page",
                owner_column=CgTestKnowledgeCategory.created_by,
                dept_column=getattr(CgTestKnowledgeCategory, "owner_dept_id", None),
            )
        items, total = await self.repo.page_admin(query, data_scope_filter)
        records = to_schema_list(CgTestKnowledgeCategorySchema, items)
        return build_page(query, total, records)

    async def _to_schema_with_parent_name(self, item: object) -> CgTestKnowledgeCategoryDetailSchema:
        schemas = await self._attach_parent_names([to_schema(CgTestKnowledgeCategoryDetailSchema, item)])
        return schemas[0]

    async def _attach_parent_names(
        self, items: list[CgTestKnowledgeCategoryDetailSchema]
    ) -> list[CgTestKnowledgeCategoryDetailSchema]:
        parent_ids = {item.parent_id for item in items if item.parent_id}
        parent_name_map = await self.repo.get_parent_name_map(parent_ids)
        for item in items:
            item.parent_id_name = parent_name_map.get(item.parent_id or "")
        return items

    async def tree(
        self,
        query: KeywordQuery,
        session: SessionPayload | None = None,
    ) -> list[CgTestKnowledgeCategoryTreeNode]:
        data_scope_filter = None
        if session is not None:
            data_scope_filter = await build_data_scope_filter(
                self.db,
                session,
                "biz:cgtestknowledgecategory:list",
                owner_column=CgTestKnowledgeCategory.created_by,
                dept_column=getattr(CgTestKnowledgeCategory, "owner_dept_id", None),
            )
        items = await self.repo.list_tree(query.keyword, data_scope_filter)
        return _build_cg_test_knowledge_category_tree(items)


def _build_cg_test_knowledge_category_tree(items) -> list[CgTestKnowledgeCategoryTreeNode]:
    ids = {item.id for item in items}
    node_map = {item.id: to_schema(CgTestKnowledgeCategoryTreeNode, item) for item in items}
    for node in node_map.values():
        node.weight = 0
        node.children = None
    roots: list[CgTestKnowledgeCategoryTreeNode] = []
    for item in items:
        node = node_map[item.id]
        parent_id = getattr(item, "parent_id", None)
        if parent_id and parent_id in ids:
            parent = node_map[parent_id]
            if parent.children is None:
                parent.children = []
            parent.children.append(node)
        else:
            roots.append(node)
    return roots


class CgTestKnowledgeDocService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CgTestKnowledgeDocRepository(db)

    async def create(self, payload: CgTestKnowledgeDocCreateRequest) -> None:
        async with transactional(self.db):
            entity = await self.repo.create(payload)
        audit_snapshots.created_entity(entity)

    async def update(self, payload: CgTestKnowledgeDocUpdateRequest) -> None:
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

    async def detail(self, query: IdQuery) -> CgTestKnowledgeDocSchema:
        schema = to_schema(CgTestKnowledgeDocSchema, await self.repo.get_required(query.id))
        return schema

    async def page_admin(self, query: CgTestKnowledgeDocAdminPageQuery) -> PageData[CgTestKnowledgeDocSchema]:
        items, total = await self.repo.page_admin(query)
        records = to_schema_list(CgTestKnowledgeDocSchema, items)
        return build_page(query, total, records)
