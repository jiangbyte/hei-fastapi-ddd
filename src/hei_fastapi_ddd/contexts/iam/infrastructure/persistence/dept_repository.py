"""Author: Charlie

部门仓储实现：实现 domain 端口，不依赖 api Schema。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.dept_po import SysDept
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.reference_guard import (
    count_dept_references,
    ensure_not_self_or_descendant,
    ensure_parent_exists,
    raise_if_referenced,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.mapping_util import mapping_data
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.row_mapper import po_row
from hei_fastapi_ddd.shared.persistence.compat import like_contains
from hei_fastapi_ddd.shared.security.data_scope import build_data_scope_filter
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.types.business import NotFoundError


class DeptRepositoryImpl:
    """部门仓储实现。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_entity(self, dept_id: str) -> SysDept:
        entity = await self.db.get(SysDept, dept_id)
        if entity is None:
            raise NotFoundError("Dept not found")
        return entity

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        parent_id = data.get("parent_id")
        await ensure_parent_exists(self.db, SysDept, parent_id, "Dept")
        entity = SysDept(**dict(data))
        self.db.add(entity)
        await self.db.flush()
        return po_row(entity)

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        return po_row(await self._get_entity(entity_id))

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None:
        entity = await self._get_entity(entity_id)
        parent_id = data.get("parent_id")
        await ensure_parent_exists(self.db, SysDept, parent_id, "Dept")
        await ensure_not_self_or_descendant(
            self.db, SysDept, entity_id, parent_id, "Dept"
        )
        for key, value in data.items():
            if key == "id":
                continue
            setattr(entity, key, value)
        entity.updated_at = datetime.now(UTC)
        await self.db.flush()

    async def delete_many(self, dept_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return
        stmt = select(SysDept.id).where(SysDept.id.in_(unique_ids))
        existing_ids = set((await self.db.execute(stmt)).scalars().all())
        if len(existing_ids) != len(unique_ids):
            raise NotFoundError("Dept not found")
        raise_if_referenced("Dept", await count_dept_references(self.db, unique_ids))
        await self.db.execute(delete(SysDept).where(SysDept.id.in_(unique_ids)))

    async def count_depts_in_scope(
        self,
        dept_ids: list[str],
        *,
        session: SessionPayload,
        permission: str,
    ) -> int:
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return 0
        data_scope_filter = await build_data_scope_filter(
            self.db,
            session,
            permission,
            owner_column=SysDept.created_by,
            dept_column=SysDept.id,
        )
        stmt = select(func.count(SysDept.id)).where(
            SysDept.id.in_(unique_ids), data_scope_filter
        )
        return int((await self.db.execute(stmt)).scalar_one())

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
        session: SessionPayload | None = None,
        permission: str = "iam:dept:page",
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[SysDept]] = select(SysDept)
        count_stmt = select(func.count(SysDept.id))
        where: list[Any] = []
        if filters.get("name"):
            where.append(like_contains(SysDept.name, filters["name"]))
        if filters.get("category"):
            where.append(SysDept.category == filters["category"])
        if filters.get("parent_id"):
            where.append(SysDept.parent_id == filters["parent_id"])
        if filters.get("status"):
            where.append(SysDept.status == filters["status"])
        if session is not None:
            scope = await build_data_scope_filter(
                self.db,
                session,
                permission,
                owner_column=SysDept.created_by,
                dept_column=SysDept.id,
            )
            if scope is not None:
                where.append(scope)
        if where:
            stmt = stmt.where(*where)
            count_stmt = count_stmt.where(*where)
        stmt = stmt.order_by(SysDept.sort.asc(), SysDept.id.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return [po_row(item) for item in items], total

    async def list_by_ids(self, dept_ids: list[str]) -> list[dict[str, Any]]:
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return []
        stmt = select(SysDept).where(SysDept.id.in_(unique_ids))
        return [po_row(item) for item in (await self.db.execute(stmt)).scalars().all()]

    async def get_dept_tree(
        self,
        *,
        session: SessionPayload | None = None,
        permission: str = "iam:dept:tree",
    ) -> list[dict[str, Any]]:
        stmt = select(SysDept).order_by(SysDept.sort.asc())
        if session is not None:
            scope = await build_data_scope_filter(
                self.db,
                session,
                permission,
                owner_column=SysDept.created_by,
                dept_column=SysDept.id,
            )
            if scope is not None:
                stmt = stmt.where(scope)
        depts = list((await self.db.execute(stmt)).scalars().all())
        ids = {dept.id for dept in depts}
        node_map: dict[str, dict[str, Any]] = {}
        for dept in depts:
            node_map[dept.id] = {
                **po_row(dept),
                "weight": dept.sort or 0,
                "master_name": None,
                "deputy_master_name": None,
                "children": [],
            }
        roots: list[dict[str, Any]] = []
        for dept in depts:
            parent_id = dept.parent_id
            if parent_id and parent_id in ids:
                node_map[parent_id]["children"].append(node_map[dept.id])
            else:
                roots.append(node_map[dept.id])
        return roots

    async def resolve_account_names(self, account_ids: list[str]) -> dict[str, str]:
        unique_ids = list(dict.fromkeys(account_ids))
        if not unique_ids:
            return {}
        from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
        from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.admin_po import (
            ProfileUserAdmin,
        )

        stmt = (
            select(SysAccount.id, ProfileUserAdmin.nickname)
            .outerjoin(ProfileUserAdmin, ProfileUserAdmin.account_id == SysAccount.id)
            .where(SysAccount.id.in_(unique_ids))
        )
        rows = (await self.db.execute(stmt)).all()
        return {row[0]: (row[1] or row[0]) for row in rows}

    async def resolve_dept_names(self, dept_ids: list[str]) -> dict[str, str]:
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return {}
        stmt = select(SysDept.id, SysDept.name).where(SysDept.id.in_(unique_ids))
        rows = (await self.db.execute(stmt)).all()
        return {row[0]: row[1] for row in rows}


DeptRepository = DeptRepositoryImpl
