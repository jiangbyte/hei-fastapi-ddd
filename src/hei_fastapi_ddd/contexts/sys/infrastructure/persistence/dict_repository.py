""" Author: Charlie

字典仓储实现：PO ↔ 领域聚合映射，实现 domain.DictRepository 协议。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select, delete, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.domain.dict.aggregate import DictAggregate
from hei_fastapi_ddd.contexts.sys.domain.dict.repository import DictTreeRecord
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.dict_po import SysDict
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.compat import like_contains
from hei_fastapi_ddd.types.business import ConflictError, NotFoundError


def _row(po: SysDict) -> dict[str, Any]:
    """PO → 行字典。"""
    mapper = inspect(po).mapper
    return {attr.key: getattr(po, attr.key) for attr in mapper.column_attrs}


class DictRepositoryImpl:
    """字典仓储，负责 PO 持久化与聚合映射。"""

    def __init__(self, db: AsyncSession):
        """绑定数据库会话。"""
        self.db = db

    async def find_by_id(self, id: str) -> DictAggregate | None:
        """按主键加载聚合。"""
        po = await self.db.get(SysDict, id)
        return self._to_domain(po) if po is not None else None

    async def find_by_code(self, code: str) -> DictAggregate | None:
        """按编码加载聚合。"""
        stmt = select(SysDict).where(SysDict.code == code).limit(1)
        po = (await self.db.execute(stmt)).scalar_one_or_none()
        return self._to_domain(po) if po is not None else None

    async def get_required(self, dict_id: str) -> DictAggregate:
        """按主键加载；不存在则抛业务异常。"""
        entity = await self.find_by_id(dict_id)
        if entity is None:
            raise NotFoundError("Dict not found")
        return entity

    async def save(self, entity: DictAggregate) -> DictAggregate:
        """新增或更新聚合（code 唯一性在应用层/此处预校验）。"""
        # 1. 编码唯一性预校验，避免落库冲突
        duplicate = await self._get_po_by_code(entity.code)
        if duplicate is not None and duplicate.id != entity.id:
            raise ConflictError("Dict code already exists")
        # 2. 按主键加载或新建 PO
        po = await self.db.get(SysDict, entity.id)
        if po is None:
            po = SysDict(id=entity.id)
            self.db.add(po)
        # 3. 回写字段并 flush
        self._apply_domain(po, entity)
        await self.db.flush()
        return entity

    async def create_from_fields(
        self,
        *,
        code: str,
        label: str | None,
        value: str | None,
        color: str | None,
        category: str | None,
        parent_id: str | None,
        status: str,
        sort: int,
    ) -> DictAggregate:
        """便捷创建：生成 ID、构造聚合并保存。"""
        # 1. 创建前唯一性检查
        if await self.find_by_code(code) is not None:
            raise ConflictError("Dict code already exists")
        # 2. 通过领域工厂校验不变量
        entity = DictAggregate.create(
            id=generate_snowflake_id(),
            code=code,
            label=label,
            value=value,
            color=color,
            category=category,
            parent_id=parent_id,
            status=status,
            sort=sort,
        )
        # 3. 持久化
        return await self.save(entity)

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除（不存在的 ID 静默跳过）。"""
        unique_ids = list(dict.fromkeys(ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysDict).where(SysDict.id.in_(unique_ids)))

    async def page_admin(
        self,
        *,
        code: str | None,
        category: str | None,
        parent_id: str | None,
        status: str | None,
        offset: int,
        size: int,
    ) -> tuple[list[DictAggregate], int]:
        """按条件后台分页。"""
        stmt: Select[tuple[SysDict]] = select(SysDict)
        count_stmt = select(func.count(SysDict.id))
        filters = []
        if code:
            filters.append(like_contains(SysDict.code, code))
        if category:
            filters.append(SysDict.category == category)
        if parent_id:
            filters.append(SysDict.parent_id == parent_id)
        if status:
            filters.append(SysDict.status == str(status))
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysDict.sort.asc(), SysDict.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [self._to_domain(item) for item in items], total

    async def get_parent_name_map(self, parent_ids: set[str]) -> dict[str, str]:
        """批量查询父级字典的名称映射。"""
        if not parent_ids:
            return {}
        stmt = select(SysDict.id, SysDict.code, SysDict.label).where(SysDict.id.in_(parent_ids))
        rows = (await self.db.execute(stmt)).all()
        return {id_: label or code for id_, code, label in rows}

    async def list_tree(self, *, category: str | None) -> list[DictTreeRecord]:
        """按分类查询字典并组装为树形结构。"""
        stmt = select(SysDict)
        if category:
            stmt = stmt.where(SysDict.category == category)
        stmt = stmt.order_by(SysDict.sort.asc())
        items = list((await self.db.execute(stmt)).scalars().all())
        return _build_tree(items)

    async def get_row_required(self, dict_id: str) -> dict[str, Any]:
        """按主键加载行字典。"""
        po = await self.db.get(SysDict, dict_id)
        if po is None:
            raise NotFoundError("Dict not found")
        return _row(po)

    async def list_rows_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        """按 ID 列表加载行字典。"""
        result: list[dict[str, Any]] = []
        for dict_id in ids:
            po = await self.db.get(SysDict, dict_id)
            if po is not None:
                result.append(_row(po))
        return result

    async def _get_po_by_code(self, code: str) -> SysDict | None:
        stmt = select(SysDict).where(SysDict.code == code).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    def _to_domain(po: SysDict) -> DictAggregate:
        return DictAggregate(
            id=po.id,
            code=po.code,
            label=po.label,
            value=po.value,
            color=po.color,
            category=po.category,
            parent_id=po.parent_id,
            status=po.status,
            sort=po.sort or 0,
        )

    @staticmethod
    def _apply_domain(po: SysDict, entity: DictAggregate) -> None:
        po.code = entity.code
        po.label = entity.label
        po.value = entity.value
        po.color = entity.color
        po.category = entity.category
        po.parent_id = entity.parent_id
        po.status = entity.status
        po.sort = entity.sort


def _entity_to_record(item: SysDict) -> DictTreeRecord:
    """将字典 PO 转为树节点记录。"""
    sort = item.sort or 0
    return {
        "id": item.id,
        "code": item.code,
        "label": item.label,
        "name": item.label,
        "value": item.value,
        "color": item.color,
        "category": item.category,
        "parent_id": item.parent_id,
        "parent_id_name": None,
        "status": item.status,
        "sort": sort,
        "weight": sort,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "children": [],
    }


def _build_tree(items: list[SysDict]) -> list[DictTreeRecord]:
    """将扁平字典列表组装为父子树。"""
    if not items:
        return []
    ids = {item.id for item in items}
    node_map: dict[str, DictTreeRecord] = {
        item.id: _entity_to_record(item) for item in items
    }
    roots: list[DictTreeRecord] = []
    for item in items:
        parent_id = item.parent_id
        if not parent_id or parent_id not in ids:
            parent_id = None
        node = node_map[item.id]
        if parent_id:
            parent = node_map[parent_id]
            node["parent_id_name"] = parent["label"] or parent["code"]
            parent["children"].append(node)
        else:
            roots.append(node)
    return roots
