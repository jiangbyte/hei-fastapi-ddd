"""Author: Charlie

IAM 审计标签端口：应用层仅依赖协议，不直连基础设施。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Protocol


class IamAuditPort(Protocol):
    """审计快照可读标签解析。"""

    def permission_bind_field(
        self,
        permission_key: str | None,
        account_type: str | None,
        data_scope: str | None,
    ) -> dict[str, Any]:
        ...

    async def role_ids_field(self, role_ids: Iterable[str]) -> dict[str, Any]:
        ...

    async def group_ids_field(self, group_ids: Iterable[str]) -> dict[str, Any]:
        ...

    async def account_ids_field(
        self,
        account_ids: Iterable[str],
        *,
        account_type: str = "admin",
    ) -> dict[str, Any]:
        ...

    async def dept_grant_field(self, grants: Sequence[Any]) -> dict[str, Any]:
        ...

    async def grant_resource_field(
        self,
        field_key: str,
        grants: Sequence[Any],
    ) -> dict[str, Any]:
        ...

    async def grant_client_resource_field(
        self,
        field_key: str,
        grants: Sequence[Any],
    ) -> dict[str, Any]:
        ...
