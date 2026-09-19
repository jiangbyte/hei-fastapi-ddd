"""Author: Charlie

dept 仓储端口。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from hei_fastapi_ddd.shared.security.session import SessionPayload


class DeptRepository(Protocol):
    """dept 仓储协议（行字典）。"""

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """创建部门并返回行。"""
        ...

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        """按主键加载，不存在则抛错。"""
        ...

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None:
        """按主键更新。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...

    async def list_by_ids(self, dept_ids: list[str]) -> list[dict[str, Any]]:
        """批量按 ID 查询。"""
        ...

    async def count_depts_in_scope(
        self,
        dept_ids: list[str],
        *,
        session: SessionPayload,
        permission: str,
    ) -> int:
        """数据范围内部门数量。"""
        ...

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
        session: SessionPayload | None = None,
        permission: str = "iam:dept:page",
    ) -> tuple[list[dict[str, Any]], int]:
        """管理端分页。"""
        ...

    async def get_dept_tree(
        self,
        *,
        session: SessionPayload | None = None,
        permission: str = "iam:dept:tree",
    ) -> list[dict[str, Any]]:
        """部门树（嵌套 children 字典）。"""
        ...

    async def resolve_account_names(self, account_ids: list[str]) -> dict[str, str]:
        """账户 ID → 展示名。"""
        ...

    async def resolve_dept_names(self, dept_ids: list[str]) -> dict[str, str]:
        """部门 ID → 名称。"""
        ...
