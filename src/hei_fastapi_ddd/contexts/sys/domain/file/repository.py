"""file 仓储端口。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from hei_fastapi_ddd.shared.security.session import SessionPayload


class FileRepository(Protocol):
    """文件元数据仓储协议。"""

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """创建文件元数据。"""
        ...

    async def get_required(self, file_id: str) -> dict[str, Any]:
        """按主键加载。"""
        ...

    async def get_by_object_name(self, object_name: str) -> dict[str, Any] | None:
        """按 object_name 加载。"""
        ...

    async def update(self, file_id: str, data: Mapping[str, Any]) -> None:
        """更新元数据。"""
        ...

    async def list_by_ids(self, file_ids: list[str]) -> list[dict[str, Any]]:
        """按 ID 列表查询。"""
        ...

    async def list_by_object_names(self, object_names: list[str]) -> list[dict[str, Any]]:
        """按 object_name 列表查询。"""
        ...

    async def delete_many(self, file_ids: list[str]) -> None:
        """批量删除。"""
        ...

    async def delete_by_id(self, file_id: str) -> None:
        """按主键删除。"""
        ...

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
        session: SessionPayload | None = None,
        permission: str = "sys:file:page",
    ) -> tuple[list[dict[str, Any]], int]:
        """后台分页（含数据权限）。"""
        ...

    async def scrub_persisted_presigned_urls(self) -> int:
        """将库内预签名 URL 刷回 object_name。"""
        ...
