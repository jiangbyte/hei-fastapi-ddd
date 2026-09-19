"""Author: Charlie

账户仓储端口（行字典，供应用层与 AccountApi 适配）。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol

from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType


class AccountRepository(Protocol):
    """账户主表、登录标识与账户侧授权关系仓储协议。"""

    async def get_by_id(self, account_id: str) -> dict[str, Any] | None:
        """按主键查询账户行。"""
        ...

    async def get_required(self, account_id: str) -> dict[str, Any]:
        """按主键查询，不存在则抛错。"""
        ...

    async def get_account_by_id(self, account_id: str) -> dict[str, Any] | None:
        """按 ID 查询账户。"""
        ...

    async def list_accounts_by_ids(self, account_ids: list[str]) -> list[dict[str, Any]]:
        """批量按 ID 查询。"""
        ...

    async def get_account_by_account(self, account: str) -> dict[str, Any] | None:
        """按主账号标识查询。"""
        ...

    async def get_account_by_identifier(
        self,
        identifier: str,
        identity_types: list[AccountIdentityType] | None = None,
    ) -> dict[str, Any] | None:
        """按登录标识解析账户。"""
        ...

    async def create(self, data: Mapping[str, Any], *, password_hash: str) -> dict[str, Any]:
        """创建账户并返回行。"""
        ...

    async def update(
        self,
        account_id: str,
        data: Mapping[str, Any],
        *,
        password_hash: str | None = None,
    ) -> None:
        """更新账户主体。"""
        ...

    async def replace_account_login_identity(self, account_id: str, account: str) -> None:
        """重建 ACCOUNT 类型登录标识。"""
        ...

    async def replace_secondary_login_identities(
        self,
        account_id: str,
        *,
        email_login_enabled: bool,
        email: str | None,
        phone_login_enabled: bool,
        phone: str | None,
    ) -> None:
        """重建 EMAIL/PHONE 登录标识。"""
        ...

    async def update_password_hash(self, account_id: str, password_hash: str) -> None:
        """更新密码哈希。"""
        ...

    async def replace_account_identities(self, account_id: str, data: Mapping[str, Any]) -> None:
        """全量重建登录标识。"""
        ...

    async def list_identities_by_account_ids(
        self, account_ids: list[str]
    ) -> list[dict[str, Any]]:
        """批量查询登录标识行。"""
        ...

    async def has_identity(self, account_id: str, identity_type: AccountIdentityType) -> bool:
        """是否拥有某类登录标识。"""
        ...

    async def upsert_account_identity(self, data: Mapping[str, Any]) -> None:
        """写入或更新单条登录标识。"""
        ...

    async def delete_many(self, account_ids: list[str]) -> None:
        """批量删除账户。"""
        ...

    async def cancel(
        self,
        account_id: str,
        *,
        cancelled_by: str,
        cancel_reason: str | None,
    ) -> dict[str, Any]:
        """注销账户并返回行。"""
        ...

    async def list_expired_cancelled_account_ids(self, cutoff: datetime) -> list[str]:
        """列出已超过保留期的注销账户 ID。"""
        ...

    async def purge_many(self, account_ids: list[str]) -> None:
        """物理清除账户及侧数据。"""
        ...

    async def count_accounts_in_scope(
        self,
        account_ids: list[str],
        *,
        session: Any,
        permission: str,
    ) -> int:
        """数据范围内账户数量。"""
        ...

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
        session: Any | None = None,
        permission: str = "iam:account:page",
    ) -> tuple[list[dict[str, Any]], int]:
        """管理端分页。"""
        ...

    async def assign_account_to_role(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """账户绑定角色。"""
        ...

    async def assign_account_to_group(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """账户绑定组。"""
        ...

    async def assign_account_to_dept(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """账户绑定部门。"""
        ...

    async def replace_account_roles(self, data: Mapping[str, Any]) -> None:
        """全量替换账户角色。"""
        ...

    async def replace_account_groups(self, data: Mapping[str, Any]) -> None:
        """全量替换账户组。"""
        ...

    async def replace_account_depts(self, data: Mapping[str, Any]) -> None:
        """全量替换账户部门。"""
        ...

    async def list_account_dept_grants(self, account_id: str) -> list[dict[str, Any]]:
        """账户部门授权列表。"""
        ...

    async def get_account_role_ids(self, account_id: str) -> list[str]:
        """账户角色 ID 列表。"""
        ...

    async def get_account_role_codes(self, account_id: str) -> list[str]:
        """账户角色编码列表。"""
        ...

    async def get_account_group_ids(self, account_id: str) -> list[str]:
        """账户组 ID 列表。"""
        ...

    async def get_account_dept_ids(self, account_id: str) -> list[str]:
        """账户部门 ID 列表。"""
        ...
