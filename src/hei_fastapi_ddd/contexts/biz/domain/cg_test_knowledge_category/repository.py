"""知识分类/文档仓储端口。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from hei_fastapi_ddd.shared.security.session import SessionPayload


class CgTestKnowledgeCategoryRepository(Protocol):
    async def create(
        self, data: Mapping[str, Any], *, owner_dept_id: str | None = None
    ) -> dict[str, Any]: ...

    async def get_required(self, entity_id: str) -> dict[str, Any]: ...

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None: ...

    async def delete_many(self, ids: list[str]) -> None: ...

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
        session: SessionPayload | None = None,
        permission: str = "biz:cgtestknowledgecategory:page",
    ) -> tuple[list[dict[str, Any]], int]: ...

    async def get_parent_name_map(self, parent_ids: set[str]) -> dict[str, str]: ...

    async def list_tree(
        self,
        keyword: str | None = None,
        *,
        session: SessionPayload | None = None,
        permission: str = "biz:cgtestknowledgecategory:list",
    ) -> list[dict[str, Any]]: ...


class CgTestKnowledgeDocRepository(Protocol):
    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]: ...

    async def get_required(self, entity_id: str) -> dict[str, Any]: ...

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None: ...

    async def delete_many(self, ids: list[str]) -> None: ...

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]: ...
