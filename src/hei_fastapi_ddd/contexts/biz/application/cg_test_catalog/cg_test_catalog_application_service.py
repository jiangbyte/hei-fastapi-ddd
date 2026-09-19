"""cg_test_catalog 应用服务：依赖 domain 仓储端口。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.biz.application.cg_test_catalog.dto import (
    CgTestCatalogCreateCommand,
    CgTestCatalogKeywordQuery,
    CgTestCatalogPageQuery,
    CgTestCatalogUpdateCommand,
)
from hei_fastapi_ddd.contexts.biz.domain.cg_test_catalog.repository import (
    CgTestCatalogRepository,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.security.data_scope import default_owner_dept_id
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page


class CgTestCatalogService:
    """目录用例编排。"""

    def __init__(self, db: AsyncSession, repo: CgTestCatalogRepository):
        self.db = db
        self.repo = repo

    async def create(
        self,
        command: CgTestCatalogCreateCommand,
        session: SessionPayload | None = None,
    ) -> None:
        async with transactional(self.db):
            entity = await self.repo.create(
                command.model_dump(),
                owner_dept_id=default_owner_dept_id(session),
            )
        audit_snapshots.created_entity(entity)

    async def update(self, command: CgTestCatalogUpdateCommand) -> None:
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
        entities = [await self.repo.get_required(entity_id) for entity_id in unique_ids]
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(unique_ids)

    async def detail(self, entity_id: str) -> dict[str, Any]:
        row = await self.repo.get_required(entity_id)
        parent_ids = {row["parent_id"]} if row.get("parent_id") else set()
        parent_name_map = await self.repo.get_parent_name_map(parent_ids)
        row = dict(row)
        row["parent_id_name"] = parent_name_map.get(row.get("parent_id") or "")
        row.setdefault("children", [])
        return row

    async def page_admin(
        self,
        query: CgTestCatalogPageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[dict]:
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
            session=session,
        )
        return build_page(query, total, items)  # type: ignore[arg-type]

    async def tree(
        self,
        query: CgTestCatalogKeywordQuery,
        session: SessionPayload | None = None,
    ) -> list[dict[str, Any]]:
        items = await self.repo.list_tree(query.keyword, session=session)
        return _build_tree(items)


def _build_tree(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids = {item["id"] for item in items}
    node_map = {item["id"]: {**item, "weight": 0, "children": None} for item in items}
    roots: list[dict[str, Any]] = []
    for item in items:
        node = node_map[item["id"]]
        parent_id = item.get("parent_id")
        if parent_id and parent_id in ids:
            parent = node_map[parent_id]
            if parent["children"] is None:
                parent["children"] = []
            parent["children"].append(node)
        else:
            roots.append(node)
    return roots
