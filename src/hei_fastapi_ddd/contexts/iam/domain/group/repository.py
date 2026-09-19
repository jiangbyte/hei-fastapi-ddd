"""group 仓储端口（行字典）。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from hei_fastapi_ddd.shared.security.session import SessionPayload


class GroupRepository(Protocol):
    """账户组仓储协议。"""

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        ...

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        ...

    async def update(self, data: Mapping[str, Any]) -> None:
        ...

    async def delete_many(self, ids: list[str]) -> None:
        ...

    async def list_by_ids(self, group_ids: list[str]) -> list[dict[str, Any]]:
        ...

    async def count_groups_in_scope(
        self,
        group_ids: list[str],
        *,
        session: SessionPayload,
        permission: str,
    ) -> int:
        ...

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
        session: SessionPayload | None = None,
        permission: str = "iam:group:page",
    ) -> tuple[list[dict[str, Any]], int]:
        ...

    async def list_accounts(
        self,
        *,
        session: SessionPayload | None = None,
        permission: str = "iam:group:ownuser",
    ) -> list[dict[str, Any]]:
        ...

    async def list_group_accounts(
        self,
        group_id: str,
        *,
        session: SessionPayload | None = None,
        permission: str = "iam:group:ownuser",
    ) -> list[dict[str, Any]]:
        ...

    async def replace_group_accounts(self, data: Mapping[str, Any]) -> None:
        ...

    async def list_account_ids_by_group(self, group_id: str) -> list[str]:
        ...

    async def list_group_role_ids(
        self,
        group_id: str,
        *,
        session: SessionPayload | None = None,
        permission: str = "iam:group:ownrole",
        account_type: str | None = None,
    ) -> list[str]:
        ...

    async def list_roles_by_ids(self, role_ids: list[str]) -> list[dict[str, Any]]:
        ...

    async def replace_group_roles(self, data: Mapping[str, Any]) -> None:
        ...
