"""弱密码库仓储端口。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class WeakPasswordRepository(Protocol):
    """弱密码库仓储协议（返回行字典）。"""

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """新增并返回行数据。"""
        ...

    async def get_required(self, row_id: str) -> dict[str, Any]:
        """按主键加载，不存在则抛错。"""
        ...

    async def update(self, row_id: str, data: Mapping[str, Any]) -> None:
        """按主键更新。"""
        ...

    async def delete_many(self, row_ids: list[str]) -> None:
        """批量删除。"""
        ...

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """后台分页。"""
        ...

    async def list_all(self, filters: Mapping[str, Any]) -> list[dict[str, Any]]:
        """列表查询。"""
        ...

    async def exists_password(self, password: str) -> bool:
        """判断密码是否存在于弱密码库。"""
        ...
