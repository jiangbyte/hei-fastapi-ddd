"""客户端模块/资源仓储端口。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from hei_fastapi_ddd.shared.config.enums import AccountType


class ClientModuleRepository(Protocol):
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

    async def list_enabled(self, account_type: AccountType | None) -> list[dict[str, Any]]:
        ...


class ClientResourceRepository(Protocol):
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

    async def list_resources(
        self,
        *,
        module_id: str | None = None,
        account_type: AccountType | None = None,
    ) -> list[dict[str, Any]]:
        ...

    async def bind_permission(self, data: Mapping[str, Any]) -> dict[str, Any]:
        ...

    async def list_module_meta_map(
        self, module_ids: list[str]
    ) -> dict[str, tuple[str, str | None]]:
        ...

    async def list_all_client_resource_grant_modules(
        self,
        account_type: AccountType | None = None,
    ) -> list[Any]:
        ...
