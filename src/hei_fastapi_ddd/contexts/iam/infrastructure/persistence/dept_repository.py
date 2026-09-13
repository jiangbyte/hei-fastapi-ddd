""" Author: Charlie

部门仓储：负责部门的增删改查、数据范围统计与树组装。
"""

from datetime import UTC, datetime
from typing import TypedDict

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from hei_fastapi_ddd.contexts.iam.application.reference_guard import (
    count_dept_references,
    ensure_not_self_or_descendant,
    ensure_parent_exists,
    raise_if_referenced,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.dept_po import SysDept
from hei_fastapi_ddd.contexts.iam.interfaces.http.dept_schemas import (
    DeptAdminPageQuery,
    DeptCreateRequest,
    DeptUpdateRequest,
)
from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.shared.persistence.compat import like_contains


class DeptTreeRecord(TypedDict):
    """部门树节点记录结构。"""

    id: str
    name: str
    category: str
    parent_id: str | None
    status: str
    sort: int
    weight: int
    is_virtual: bool
    master_id: str | None
    deputy_master_id: str | None
    master_name: str | None
    deputy_master_name: str | None
    extra: dict
    created_at: datetime
    created_by: str | None
    updated_at: datetime
    updated_by: str | None
    children: list["DeptTreeRecord"]


class DeptRepository:
    """部门仓储。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: DeptCreateRequest) -> None:
        """创建部门，父级不存在时抛冲突错误。"""
        await ensure_parent_exists(self.db, SysDept, payload.parent_id, "Dept")
        dept = SysDept(**payload.model_dump())
        self.db.add(dept)
        await self.db.flush()

    async def get_by_id(self, dept_id: str) -> SysDept | None:
        """按主键查询部门。"""
        return await self.db.get(SysDept, dept_id)

    async def get_required(self, dept_id: str) -> SysDept:
        """按主键查询部门，不存在时抛 NotFoundError。"""
        entity = await self.get_by_id(dept_id)
        if entity is None:
            raise NotFoundError("Dept not found")
        return entity

    async def update(self, payload: DeptUpdateRequest) -> None:
        """更新部门，校验父级存在及层级合法性。"""
        entity = await self.get_required(payload.id)
        await ensure_parent_exists(self.db, SysDept, payload.parent_id, "Dept")
        await ensure_not_self_or_descendant(self.db, SysDept, payload.id, payload.parent_id, "Dept")
        data = payload.model_dump(exclude={"id"})
        for key, value in data.items():
            setattr(entity, key, value)
        entity.updated_at = datetime.now(UTC)
        await self.db.flush()

    async def delete_many(self, dept_ids: list[str]) -> None:
        """删除部门，存在引用时抛冲突错误。"""
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
        data_scope_filter: ColumnElement[bool],
    ) -> int:
        """统计处于当前数据范围内的目标部门数量。"""
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return 0
        stmt = select(func.count(SysDept.id)).where(SysDept.id.in_(unique_ids), data_scope_filter)
        return int((await self.db.execute(stmt)).scalar_one())

    async def page_admin(
        self,
        query: DeptAdminPageQuery,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> tuple[list[SysDept], int]:
        """按条件分页查询部门并统计总数。"""
        stmt: Select[tuple[SysDept]] = select(SysDept)
        count_stmt = select(func.count(SysDept.id))
        filters = []
        if query.name:
            filters.append(like_contains(SysDept.name, query.name))
        if query.category:
            filters.append(SysDept.category == query.category)
        if query.parent_id:
            filters.append(SysDept.parent_id == query.parent_id)
        if query.status:
            filters.append(SysDept.status == query.status)
        if data_scope_filter is not None:
            filters.append(data_scope_filter)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysDept.sort.asc(), SysDept.id.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def list_depts(
        self,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> list[SysDept]:
        """列出部门，可按数据范围过滤。"""
        stmt = select(SysDept).order_by(SysDept.sort.asc())
        if data_scope_filter is not None:
            stmt = stmt.where(data_scope_filter)
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_by_ids(self, dept_ids: list[str]) -> list[SysDept]:
        """按 ID 列表批量查询部门。"""
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return []
        stmt = select(SysDept).where(SysDept.id.in_(unique_ids))
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_dept_tree(
        self,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> list[DeptTreeRecord]:
        """将部门列表组装为树结构（按 parent_id 挂载，对齐 hei-boot TreeUtil）。"""
        depts = await self.list_depts(data_scope_filter)
        ids = {dept.id for dept in depts}
        node_map: dict[str, DeptTreeRecord] = {
            dept.id: {
                "id": dept.id,
                "name": dept.name,
                "category": dept.category,
                "parent_id": dept.parent_id,
                "status": dept.status,
                "sort": dept.sort,
                "weight": dept.sort or 0,
                "is_virtual": dept.is_virtual,
                "master_id": dept.master_id,
                "deputy_master_id": dept.deputy_master_id,
                "master_name": None,
                "deputy_master_name": None,
                "extra": dept.extra or {},
                "created_at": dept.created_at,
                "created_by": dept.created_by,
                "updated_at": dept.updated_at,
                "updated_by": dept.updated_by,
                "children": [],
            }
            for dept in depts
        }
        roots: list[DeptTreeRecord] = []
        for dept in depts:
            parent_id = dept.parent_id
            if parent_id and parent_id in ids:
                node_map[parent_id]["children"].append(node_map[dept.id])
            else:
                roots.append(node_map[dept.id])
        return roots

    async def resolve_account_names(self, account_ids: list[str]) -> dict[str, str]:
        """批量查询账户名称，返回 {account_id: name} 映射。"""
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
        """批量查询部门名称，返回 {dept_id: name} 映射。"""
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return {}
        stmt = select(SysDept.id, SysDept.name).where(SysDept.id.in_(unique_ids))
        rows = (await self.db.execute(stmt)).all()
        return {row[0]: row[1] for row in rows}
