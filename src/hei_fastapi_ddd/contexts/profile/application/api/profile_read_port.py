"""Author: Charlie

资料读端口：供 IAM 账户读侧组装，避免 application 直连 profile 基础设施。
"""

from __future__ import annotations

from typing import Protocol


class ProfileReadPort(Protocol):
    """按 account_id 批量读取资料行字典。"""

    async def list_admin_by_account_ids(self, account_ids: list[str]) -> list[dict]:
        ...

    async def list_portal_by_account_ids(self, account_ids: list[str]) -> list[dict]:
        ...

    async def is_identity_verified(self, account_id: str) -> bool:
        """账户是否已完成实名认证。"""
        ...

    async def get_profile_by_account(
        self, account_type: str, account_id: str
    ) -> dict[str, object] | None:
        """按账户类型与 ID 查询资料行。"""
        ...

    async def get_profiles_by_account_ids(
        self, account_type: str, account_ids: list[str]
    ) -> dict[str, dict[str, object]]:
        """批量查询资料，返回 account_id → 行字典。"""
        ...
