""" Author: Charlie

字典应用服务：编排领域聚合、仓储端口与审计快照。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.domain.dict.aggregate import DictAggregate
from hei_fastapi_ddd.contexts.sys.domain.dict.repository import DictTreeRecord
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.dict_po import SysDict
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.dict_repository import DictRepository
from hei_fastapi_ddd.contexts.sys.interfaces.http.dict_schemas import (
    DictAdminPageQuery,
    DictCreateRequest,
    DictIdQuery,
    DictIdsRequest,
    DictTreeQuery,
    DictUpdateRequest,
    SysDictSchema,
    SysDictTreeNode,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page


class DictService:
    """字典应用服务，负责 CRUD、分页查询和树形响应转换。"""

    def __init__(self, db: AsyncSession):
        """绑定会话并初始化仓储。"""
        self.db = db
        self.repo = DictRepository(db)

    async def create(self, payload: DictCreateRequest) -> None:
        """事务内新增字典。"""
        # 1. 事务内通过仓储创建聚合（领域校验编码/状态）
        async with transactional(self.db):
            entity = await self.repo.create_from_fields(
                code=payload.code,
                label=payload.label,
                value=payload.value,
                color=payload.color,
                category=str(payload.category) if payload.category is not None else None,
                parent_id=payload.parent_id,
                status=str(payload.status),
                sort=int(payload.sort or 0),
            )
            # 2. 用 PO 写审计创建快照
            po = await self.repo.get_po_required(entity.id)
            audit_snapshots.created_entity(po)

    async def update(self, payload: DictUpdateRequest) -> None:
        """事务内更新字典。"""
        # 1. 加载聚合与审计前快照
        entity = await self.repo.get_required(payload.id)
        po = await self.repo.get_po_required(payload.id)
        audit_snapshots.before_entity(po)
        # 2. 领域方法更新字段
        entity.update(
            code=payload.code,
            label=payload.label,
            value=payload.value,
            color=payload.color,
            category=str(payload.category) if payload.category is not None else None,
            parent_id=payload.parent_id,
            status=str(payload.status),
            sort=int(payload.sort or 0),
        )
        # 3. 事务内保存并写后快照
        async with transactional(self.db):
            await self.repo.save(entity)
            await self.db.refresh(po)
            audit_snapshots.after_entity(po)

    async def delete(self, payload: DictIdsRequest) -> None:
        """事务内批量删除字典。"""
        # 1. 去重并收集已存在 PO 供审计
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = await self.repo.list_pos_by_ids(unique_ids)
        # 2. 事务内删除并记录快照
        async with transactional(self.db):
            audit_snapshots.deleted_all(entities)
            await self.repo.delete_many(unique_ids)

    async def get(self, query: DictIdQuery) -> SysDictSchema:
        """查询字典详情并填充父级名称。"""
        # 1. 校验存在（领域加载）
        await self.repo.get_required(query.id)
        # 2. 用 PO 组装响应（含时间戳）
        po = await self.repo.get_po_required(query.id)
        return (await self._attach_parent_names([_po_to_schema(po)]))[0]

    async def page_admin(self, query: DictAdminPageQuery) -> PageData[SysDictSchema]:
        """分页查询字典并填充父级名称。"""
        items, total = await self.repo.page_admin(
            code=query.code,
            category=query.category,
            parent_id=query.parent_id,
            status=str(query.status) if query.status else None,
            offset=query.offset,
            size=query.size,
        )
        # 分页结果经领域校验后，再按 ID 取 PO 补全时间戳字段
        schemas: list[SysDictSchema] = []
        for agg in items:
            po = await self.repo.get_po_required(agg.id)
            schemas.append(_po_to_schema(po))
        records = await self._attach_parent_names(schemas)
        return build_page(query, total, records)

    async def list_tree(self, query: DictTreeQuery) -> list[SysDictTreeNode]:
        """查询字典树。"""
        return _build_tree_nodes(await self.repo.list_tree(category=query.category))

    async def _attach_parent_names(self, items: list[SysDictSchema]) -> list[SysDictSchema]:
        """批量填充字典的父级名称。"""
        parent_ids = {item.parent_id for item in items if item.parent_id}
        parent_name_map = await self.repo.get_parent_name_map(parent_ids)
        for item in items:
            item.parent_id_name = parent_name_map.get(item.parent_id or "")
        return items


def _po_to_schema(po: SysDict) -> SysDictSchema:
    """PO 转响应 schema。"""
    return SysDictSchema(
        id=po.id,
        code=po.code,
        label=po.label,
        value=po.value,
        color=po.color,
        category=po.category,  # type: ignore[arg-type]
        parent_id=po.parent_id,
        parent_id_name=None,
        status=po.status,
        sort=po.sort or 0,
        created_at=po.created_at or datetime.now(UTC),
        created_by=getattr(po, "created_by", None),
        updated_at=po.updated_at or datetime.now(UTC),
        updated_by=getattr(po, "updated_by", None),
    )


def _build_tree_nodes(
    items: Sequence[DictTreeRecord | SysDictTreeNode | Mapping[str, object]],
) -> list[SysDictTreeNode]:
    """递归将字典树记录转换为树节点响应。"""
    nodes: list[SysDictTreeNode] = []
    for item in items:
        raw_item: Mapping[str, object] = (
            item.model_dump() if isinstance(item, SysDictTreeNode) else item
        )
        children_raw = raw_item.get("children", [])
        nodes.append(
            SysDictTreeNode(
                id=str(raw_item["id"]),
                code=str(raw_item["code"]),
                label=raw_item.get("label"),  # type: ignore[arg-type]
                name=raw_item.get("name"),  # type: ignore[arg-type]
                value=raw_item.get("value"),  # type: ignore[arg-type]
                color=raw_item.get("color"),  # type: ignore[arg-type]
                category=raw_item.get("category"),  # type: ignore[arg-type]
                parent_id=raw_item.get("parent_id"),  # type: ignore[arg-type]
                parent_id_name=raw_item.get("parent_id_name"),  # type: ignore[arg-type]
                status=str(raw_item["status"]),
                sort=int(raw_item["sort"]),
                weight=int(raw_item.get("weight", raw_item["sort"])),
                created_at=raw_item.get("created_at"),  # type: ignore[arg-type]
                updated_at=raw_item.get("updated_at"),  # type: ignore[arg-type]
                children=_build_tree_nodes(children_raw),  # type: ignore[arg-type]
            )
        )
    return nodes


# 供类型检查引用，避免未使用告警
_ = DictAggregate
