"""codegen 仓储端口。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

class CodegenRepository(Protocol):
    """代码生成方案与字段仓储（行字典）。"""

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """创建方案。"""
        ...

    async def get_by_id(self, plan_id: str) -> dict[str, Any] | None:
        """按主键查询。"""
        ...

    async def get_required(self, plan_id: str) -> dict[str, Any]:
        """按主键查询，不存在抛错。"""
        ...

    async def update(self, plan_id: str, data: Mapping[str, Any]) -> None:
        """更新方案。"""
        ...

    async def delete_many(self, plan_ids: list[str]) -> None:
        """批量删除方案及字段。"""
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

    async def list_fields(
        self, plan_id: str, table_role: str | None = None
    ) -> list[dict[str, Any]]:
        """查询字段配置。"""
        ...

    async def replace_fields(
        self, plan_id: str, fields: list[Mapping[str, Any]]
    ) -> None:
        """整体替换字段配置。"""
        ...

    async def upsert_reflected_fields(
        self,
        plan_id: str,
        table_role: str,
        fields: list[Mapping[str, Any]],
    ) -> None:
        """合并反射字段。"""
        ...

    async def list_resource_options(self, module_id: str | None = None) -> list[dict[str, Any]]:
        """父资源选项。"""
        ...

    async def list_database_tables(self) -> list[dict[str, str | None]]:
        """内省数据库表。"""
        ...

    async def list_database_columns(self, table_name: str) -> list[dict[str, Any]]:
        """内省表列。"""
        ...
