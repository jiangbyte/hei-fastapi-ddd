"""系统配置仓储端口。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class ConfigRepository(Protocol):
    """系统配置仓储协议。"""

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """新增配置。"""
        ...

    async def get_required(self, config_id: str) -> dict[str, Any]:
        """按主键加载。"""
        ...

    async def get_by_key(self, config_key: str) -> dict[str, Any] | None:
        """按 config_key 加载。"""
        ...

    async def update(self, config_id: str, data: Mapping[str, Any]) -> None:
        """按主键更新。"""
        ...

    async def delete_many(self, config_ids: list[str]) -> None:
        """批量删除。"""
        ...

    async def list_by_ids(self, config_ids: list[str]) -> list[dict[str, Any]]:
        """按主键分批查询。"""
        ...

    async def list_by_category(self, category: str | None = None) -> list[dict[str, Any]]:
        """按分类查询。"""
        ...

    async def batch_save(self, items: Sequence[Mapping[str, Any]]) -> None:
        """按 config_key upsert。"""
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
