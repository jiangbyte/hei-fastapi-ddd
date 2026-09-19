"""工作台只读查询端口。"""

from __future__ import annotations

from typing import Protocol


class WorkspaceReadPort(Protocol):
    async def load_menus(self, resource_ids: list[str]) -> dict[str, dict]: ...
    async def has_super_admin_role(self, role_ids: list[str]) -> bool: ...
    async def list_recent_activities(
        self, account_id: str, *, login_only: bool, exclude_login: bool, limit: int
    ) -> list[dict]: ...
