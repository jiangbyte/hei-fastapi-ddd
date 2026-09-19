""" Author: Charlie

notice 仓储端口。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol


class NoticeRepository(Protocol):
    """notice 仓储协议（行字典）。"""

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """创建消息。"""
        ...

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        """按主键加载。"""
        ...

    async def get_by_id(self, entity_id: str) -> dict[str, Any] | None:
        """按主键加载，不存在返回 None。"""
        ...

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None:
        """更新消息。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...

    async def publish_many(
        self,
        entity_ids: list[str],
        *,
        now: datetime,
        sender_account_type: str,
        sender_account_id: str,
    ) -> None:
        """批量发布。"""
        ...

    async def revoke_many(self, entity_ids: list[str], *, now: datetime) -> None:
        """批量撤回。"""
        ...

    async def find_published_visible(
        self,
        entity_id: str,
        account_type: str,
        account_id: str | None = None,
    ) -> dict[str, Any] | None:
        """查询已发布且可见的消息。"""
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
        account_type: str,
        account_id: str | None = None,
        *,
        kind: str | None = None,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int, set[str]]:
        """用户可见消息分页。"""
        ...

    async def count_unread(self, account_type: str, account_id: str) -> int:
        """未读数量。"""
        ...

    async def mark_read(self, ids: list[str], account_type: str, account_id: str) -> None:
        """标记已读。"""
        ...

    async def mark_all_read(self, account_type: str, account_id: str) -> None:
        """全部已读。"""
        ...

    async def increment_view_count(self, entity_id: str) -> None:
        """自增查看次数。"""
        ...

    async def update_pin(
        self,
        entity_id: str,
        *,
        is_pinned: bool,
        pinned_until: datetime | None,
    ) -> dict[str, Any]:
        """更新置顶。"""
        ...

    async def list_read_ids(
        self,
        notice_ids: list[str],
        account_type: str,
        account_id: str,
    ) -> set[str]:
        """已读 ID 集合。"""
        ...
