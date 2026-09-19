"""资源仓储端口（行字典 / 结构化 dict）。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.security.session import SessionPayload


class ResourceRepository(Protocol):
    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        ...

    async def get_required(self, resource_id: str) -> dict[str, Any]:
        ...

    async def update(self, data: Mapping[str, Any]) -> None:
        ...

    async def delete_many(self, ids: list[str]) -> None:
        ...

    async def list_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        ...

    async def page_admin(
        self,
        query: Mapping[str, Any],
    ) -> tuple[list[dict[str, Any]], int]:
        ...

    async def page_buttons(
        self,
        query: Mapping[str, Any],
    ) -> tuple[list[dict[str, Any]], int]:
        ...

    async def bind_resource_permission(self, data: Mapping[str, Any]) -> dict[str, Any]:
        ...

    async def replace_resource_permission(self, data: Mapping[str, Any]) -> None:
        ...

    async def delete_buttons(self, ids: list[str]) -> None:
        ...

    async def list_resources(
        self,
        *,
        module_id: str | None = None,
        module_client: AccountType | None = None,
    ) -> list[dict[str, Any]]:
        ...

    async def list_resources_by_ids_with_parents(
        self,
        resource_ids: list[str],
        *,
        module_client: AccountType | None = None,
    ) -> list[dict[str, Any]]:
        ...

    async def list_all_resource_grant_modules(
        self,
        module_client: AccountType | None = None,
    ) -> list[Any]:
        ...

    async def list_module_meta_map(
        self, module_ids: list[str]
    ) -> dict[str, tuple[str, str | None]]:
        ...

    async def list_permissions_by_resource_ids(
        self, resource_ids: list[str]
    ) -> dict[str, list[Any]]:
        ...

    async def list_parent_names(self, parent_ids: list[str]) -> dict[str, str]:
        ...


class ResourceModuleRepository(Protocol):
    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        ...

    async def get_required(self, module_id: str) -> dict[str, Any]:
        ...

    async def update(self, data: Mapping[str, Any]) -> None:
        ...

    async def delete_many(self, ids: list[str]) -> None:
        ...

    async def list_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        ...

    async def page_admin(
        self,
        query: Mapping[str, Any],
    ) -> tuple[list[dict[str, Any]], int]:
        ...

    async def list_enabled_modules(
        self, client: AccountType | None
    ) -> list[dict[str, Any]]:
        ...
