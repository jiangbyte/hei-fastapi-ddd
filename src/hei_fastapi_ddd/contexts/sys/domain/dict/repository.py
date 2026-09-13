""" Author: Charlie

字典仓储端口：应用层依赖此协议，由基础设施实现。
"""

from __future__ import annotations

from typing import Protocol, TypedDict

from hei_fastapi_ddd.contexts.sys.domain.dict.aggregate import DictAggregate


class DictTreeRecord(TypedDict):
    """字典树节点记录（跨层传输的轻量结构）。"""

    id: str
    code: str
    label: str | None
    name: str | None
    value: str | None
    color: str | None
    category: str | None
    parent_id: str | None
    parent_id_name: str | None
    status: str
    sort: int
    weight: int
    created_at: object
    updated_at: object
    children: list["DictTreeRecord"]


class DictRepository(Protocol):
    """字典仓储协议。"""

    async def find_by_id(self, id: str) -> DictAggregate | None:
        """按主键加载聚合。"""
        ...

    async def find_by_code(self, code: str) -> DictAggregate | None:
        """按编码加载聚合。"""
        ...

    async def save(self, entity: DictAggregate) -> DictAggregate:
        """新增或更新聚合。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...

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
        """后台分页查询。"""
        ...

    async def get_parent_name_map(self, parent_ids: set[str]) -> dict[str, str]:
        """批量解析父级显示名。"""
        ...

    async def list_tree(self, *, category: str | None) -> list[DictTreeRecord]:
        """按分类组装字典树。"""
        ...
