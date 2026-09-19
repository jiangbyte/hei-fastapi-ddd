"""Author: Charlie

role 仓储端口（行字典）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from hei_fastapi_ddd.shared.security.session import SessionPayload


class RoleRepository(Protocol):
    """role 仓储协议。"""

    async def create(self, data: Mapping[str, Any]) -> None:
        ...

    async def get_by_code(self, code: str) -> dict[str, Any] | None:
        ...

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        ...

    async def update(self, data: Mapping[str, Any]) -> None:
        ...

    async def delete_many(self, ids: list[str]) -> None:
        ...

    async def list_by_ids(self, role_ids: list[str]) -> list[dict[str, Any]]:
        ...

    async def count_roles_in_scope(
        self,
        role_ids: list[str],
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
        permission: str = "iam:role:page",
    ) -> tuple[list[dict[str, Any]], int]:
        ...

    async def list_resource_grants(
        self,
        role_id: str,
        *,
        account_type: str | None = None,
    ) -> list[dict[str, Any]]:
        ...

    async def replace_resource_grants(self, data: Mapping[str, Any]) -> None:
        ...

    async def list_account_ids_by_role(self, role_id: str) -> list[str]:
        ...

    async def list_accounts(
        self,
        *,
        session: SessionPayload | None = None,
        permission: str = "iam:role:ownuser",
    ) -> list[dict[str, Any]]:
        ...

    async def list_role_accounts(
        self,
        role_id: str,
        *,
        session: SessionPayload | None = None,
        permission: str = "iam:role:ownuser",
    ) -> list[dict[str, Any]]:
        ...

    async def replace_role_accounts(self, data: Mapping[str, Any]) -> None:
        ...

    async def resolve_dept_names(self, dept_ids: list[str]) -> dict[str, str]:
        ...
