""" Author: Charlie

字典应用服务：编排领域聚合与仓储端口，不依赖 infrastructure / api。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.dict.dto import (
    DictAdminPageQuery,
    DictCreateCommand,
    DictIdQuery,
    DictIdsCommand,
    DictTreeQuery,
    DictUpdateCommand,
)
from hei_fastapi_ddd.contexts.sys.domain.dict.repository import DictRepository, DictTreeRecord
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page


class DictService:
    """字典应用服务，负责 CRUD、分页查询和树形数据。"""

    def __init__(self, db: AsyncSession, repo: DictRepository):
        """绑定会话与仓储端口。"""
        self.db = db
        self.repo = repo

    async def create(self, command: DictCreateCommand) -> None:
        """事务内新增字典。"""
        # 1. 事务内通过仓储创建聚合（领域校验编码/状态）
        async with transactional(self.db):
            entity = await self.repo.create_from_fields(
                code=command.code,
                label=command.label,
                value=command.value,
                color=command.color,
                category=command.category,
                parent_id=command.parent_id,
                status=command.status,
                sort=command.sort,
            )
            # 2. 行字典写审计创建快照
            row = await self.repo.get_row_required(entity.id)
            audit_snapshots.created_entity(row)

    async def update(self, command: DictUpdateCommand) -> None:
        """事务内更新字典。"""
        # 1. 加载聚合与审计前快照
        entity = await self.repo.get_required(command.id)
        before_row = await self.repo.get_row_required(command.id)
        audit_snapshots.before_entity(before_row)
        # 2. 领域方法更新字段
        entity.update(
            code=command.code,
            label=command.label,
            value=command.value,
            color=command.color,
            category=command.category,
            parent_id=command.parent_id,
            status=command.status,
            sort=command.sort,
        )
        # 3. 事务内保存并写后快照
        async with transactional(self.db):
            await self.repo.save(entity)
            after_row = await self.repo.get_row_required(command.id)
            audit_snapshots.after_entity(after_row)

    async def delete(self, command: DictIdsCommand) -> None:
        """事务内批量删除字典。"""
        # 1. 去重并收集已存在行供审计
        unique_ids = list(dict.fromkeys(command.ids))
        rows = await self.repo.list_rows_by_ids(unique_ids)
        # 2. 事务内删除并记录快照
        async with transactional(self.db):
            audit_snapshots.deleted_all(rows)
            await self.repo.delete_many(unique_ids)

    async def get(self, query: DictIdQuery) -> dict[str, object]:
        """查询字典详情并填充父级名称。"""
        # 1. 校验存在并取行数据
        row = await self.repo.get_row_required(query.id)
        # 2. 批量解析父级名称
        items = await self._attach_parent_names([row])
        return items[0]

    async def page_admin(self, query: DictAdminPageQuery) -> PageData[dict]:
        """分页查询字典并填充父级名称。"""
        # 1. 仓储分页（领域聚合）
        aggregates, total = await self.repo.page_admin(
            code=query.code,
            category=query.category,
            parent_id=query.parent_id,
            status=query.status,
            offset=query.offset,
            size=query.size,
        )
        # 2. 按 ID 取行字典补全时间戳等列
        rows: list[dict[str, object]] = []
        for agg in aggregates:
            rows.append(await self.repo.get_row_required(agg.id))
        records = await self._attach_parent_names(rows)
        return build_page(query, total, records)  # type: ignore[arg-type]

    async def list_tree(self, query: DictTreeQuery) -> list[DictTreeRecord]:
        """查询字典树。"""
        return await self.repo.list_tree(category=query.category)

    async def _attach_parent_names(
        self, items: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        """批量填充字典的父级名称。"""
        parent_ids = {str(item["parent_id"]) for item in items if item.get("parent_id")}
        parent_name_map = await self.repo.get_parent_name_map(parent_ids)
        for item in items:
            parent_id = item.get("parent_id")
            if parent_id:
                item["parent_id_name"] = parent_name_map.get(str(parent_id))
        return items


def build_tree_nodes_from_records(
    items: Sequence[DictTreeRecord | Mapping[str, object]],
) -> list[dict[str, object]]:
    """将字典树记录转为嵌套 dict（trigger 再映射 HTTP Schema）。"""
    nodes: list[dict[str, object]] = []
    for item in items:
        raw: Mapping[str, object] = dict(item) if isinstance(item, Mapping) else item  # type: ignore[assignment]
        children_raw = raw.get("children", [])
        nodes.append(
            {
                **raw,
                "children": build_tree_nodes_from_records(children_raw),  # type: ignore[arg-type]
            }
        )
    return nodes
