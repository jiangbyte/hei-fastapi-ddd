"""Author: Charlie

position 仓储端口。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from hei_fastapi_ddd.shared.security.session import SessionPayload


class PositionRepository(Protocol):
    """position 仓储协议（行字典）。"""

    async def create(
        self,
        data: Mapping[str, Any],
        *,
        owner_dept_id: str | None = None,
    ) -> dict[str, Any]:
        """新增职位并返回行数据。"""
        ...

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        """按主键加载，不存在则抛错。"""
        ...

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None:
        """按主键更新字段。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...

    async def count_positions_in_scope(
        self,
        position_ids: list[str],
        *,
        session: SessionPayload,
        permission: str,
    ) -> int:
        """统计处于数据范围内的职位数量。"""
        ...

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
        session: SessionPayload | None = None,
        permission: str = "iam:position:page",
    ) -> tuple[list[dict[str, Any]], int]:
        """管理端分页（含数据权限）。"""
        ...
