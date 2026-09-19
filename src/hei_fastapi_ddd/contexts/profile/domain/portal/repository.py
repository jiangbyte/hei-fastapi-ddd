""" Author: Charlie

门户资料仓储端口（行字典，供应用层依赖）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class ProfileUserPortalRepository(Protocol):
    """门户资料仓储协议。"""

    async def get_by_account_id(self, account_id: str) -> dict[str, Any] | None:
        """按账户 ID 查询资料行。"""
        ...

    async def upsert(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """创建或更新资料。"""
        ...

    async def update_avatar(self, account_id: str, avatar: str) -> dict[str, Any]:
        """仅更新头像字段。"""
        ...

    async def list_by_account_ids(self, account_ids: list[str]) -> list[dict[str, Any]]:
        """批量查询资料行。"""
        ...
