"""Author: Charlie

IAM 对外账户 API 端口：供 auth 等上下文依赖，避免直连基础设施。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol

from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.shared.security.password import verify_password_async


class AccountApi(Protocol):
    """跨上下文账户查询/写入端口。"""

    async def get_account_by_id(self, account_id: str) -> dict[str, Any] | None:
        """按账户 ID 获取账户行。"""
        ...

    async def get_by_id(self, account_id: str) -> dict[str, Any] | None:
        """按 ID 获取账户行（OAuth 等链路）。"""
        ...

    async def get_required(self, account_id: str) -> dict[str, Any]:
        """按 ID 获取账户，不存在则抛错。"""
        ...

    async def get_account_by_identifier(
        self,
        identifier: str,
        identity_types: list[AccountIdentityType] | None = None,
    ) -> dict[str, Any] | None:
        """按登录标识解析账户。"""
        ...

    async def list_accounts_by_ids(self, account_ids: list[str]) -> list[dict[str, Any]]:
        """批量加载账户行。"""
        ...

    async def list_identities_by_account_ids(
        self, account_ids: list[str]
    ) -> list[dict[str, Any]]:
        """批量加载登录标识。"""
        ...

    async def has_identity(self, account_id: str, identity_type: AccountIdentityType) -> bool:
        """是否拥有某类登录标识。"""
        ...

    async def create_account(
        self,
        data: Mapping[str, Any],
        *,
        password_hash: str,
    ) -> dict[str, Any]:
        """创建账户（注册/ OAuth 开户）。"""
        ...

    async def update_password_hash(self, account_id: str, password_hash: str) -> None:
        """更新密码哈希。"""
        ...

    async def assign_account_to_role(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """分配默认角色。"""
        ...

    async def assign_account_to_dept(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """分配默认部门。"""
        ...

    async def cancel(
        self,
        account_id: str,
        *,
        cancelled_by: str,
        cancel_reason: str | None,
    ) -> dict[str, Any]:
        """注销账户。"""
        ...

    async def upsert_account_identity(
        self,
        account_id: str,
        identity_type: AccountIdentityType,
        identifier: str | None,
        *,
        verified: bool = True,
        enabled: bool = True,
    ) -> None:
        """写入或更新单条登录标识。"""
        ...

    async def verify_password(self, account_row: Mapping[str, Any], plain_password: str) -> bool:
        """校验明文密码与账户行中的 password_hash。"""
        ...


async def verify_account_password(account_row: Mapping[str, Any], plain_password: str) -> bool:
    """端口层密码校验辅助（不暴露基础设施）。"""
    password_hash = str(account_row.get("password_hash") or "")
    if not password_hash:
        return False
    return await verify_password_async(plain_password, password_hash)
