"""feedback 仓储端口。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class SysFeedbackRepository(Protocol):
    """反馈仓储协议（行字典）。"""

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """创建反馈。"""
        ...

    async def get_by_id(self, entity_id: str) -> dict[str, Any] | None:
        """按主键查询。"""
        ...

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        """按主键查询，不存在抛错。"""
        ...

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None:
        """更新反馈字段。"""
        ...

    async def delete_many(self, entity_ids: list[str]) -> None:
        """批量删除。"""
        ...

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """管理端分页。"""
        ...

    async def page_my(
        self,
        filters: Mapping[str, Any],
        *,
        account_type: str,
        account_id: str,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """当前用户分页。"""
        ...
