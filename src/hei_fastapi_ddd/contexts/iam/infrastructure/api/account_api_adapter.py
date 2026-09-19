"""Author: Charlie

AccountApi 适配器：用账户仓储端口实现跨上下文 API。
"""

from __future__ import annotations

from collections.abc import Mapping
from types import SimpleNamespace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.api.account_api import (
    AccountApi,
    verify_account_password,
)
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import (
    AccountRepositoryImpl,
)


def _as_row_obj(row: dict[str, Any]) -> Any:
    """过渡期：auth 仍按属性访问账户行。"""
    return SimpleNamespace(**row)


class AccountApiAdapter:
    """将 AccountRepositoryImpl 适配为 AccountApi。"""

    def __init__(self, db: AsyncSession):
        self._repo = AccountRepositoryImpl(db)

    async def get_account_by_id(self, account_id: str) -> dict[str, Any] | None:
        return await self._repo.get_account_by_id(account_id)

    async def get_by_id(self, account_id: str) -> dict[str, Any] | None:
        return await self._repo.get_by_id(account_id)

    async def get_required(self, account_id: str) -> dict[str, Any]:
        return await self._repo.get_required(account_id)

    async def get_account_by_identifier(
        self,
        identifier: str,
        identity_types: list[AccountIdentityType] | None = None,
    ) -> dict[str, Any] | None:
        return await self._repo.get_account_by_identifier(identifier, identity_types=identity_types)

    async def list_accounts_by_ids(self, account_ids: list[str]) -> list[dict[str, Any]]:
        return await self._repo.list_accounts_by_ids(account_ids)

    async def list_identities_by_account_ids(
        self, account_ids: list[str]
    ) -> list[dict[str, Any]]:
        return await self._repo.list_identities_by_account_ids(account_ids)

    async def has_identity(self, account_id: str, identity_type: AccountIdentityType) -> bool:
        return await self._repo.has_identity(account_id, identity_type)

    async def create_account(
        self,
        data: Mapping[str, Any],
        *,
        password_hash: str,
    ) -> dict[str, Any]:
        return await self._repo.create(data, password_hash=password_hash)

    async def create(self, payload: Any, *, password_hash: str) -> Any:
        """过渡期：兼容 auth 注册链路对 AccountCreateRequest 的调用。"""
        raw = payload.model_dump() if hasattr(payload, "model_dump") else dict(payload)
        return _as_row_obj(await self._repo.create(raw, password_hash=password_hash))

    async def update_password_hash(self, account_id: str, password_hash: str) -> None:
        await self._repo.update_password_hash(account_id, password_hash)

    async def assign_account_to_role(self, data: Mapping[str, Any]) -> dict[str, Any]:
        return await self._repo.assign_account_to_role(data)

    async def assign_account_to_dept(self, data: Mapping[str, Any]) -> dict[str, Any]:
        return await self._repo.assign_account_to_dept(data)

    async def cancel(
        self,
        account_id: str,
        *,
        cancelled_by: str,
        cancel_reason: str | None,
    ) -> dict[str, Any]:
        return await self._repo.cancel(
            account_id,
            cancelled_by=cancelled_by,
            cancel_reason=cancel_reason,
        )

    async def upsert_account_identity(
        self,
        account_id: str,
        identity_type: AccountIdentityType,
        identifier: str | None,
        *,
        verified: bool = True,
        enabled: bool = True,
    ) -> None:
        await self._repo.upsert_account_identity(
            account_id,
            identity_type,
            identifier,
            verified=verified,
            enabled=enabled,
        )

    async def verify_password(self, account_row: Mapping[str, Any], plain_password: str) -> bool:
        return await verify_account_password(account_row, plain_password)

    def __getattr__(self, name: str) -> Any:
        """过渡期：未显式声明的方法仍转发仓储（auth 逐步迁移后删除）。"""
        attr = getattr(self._repo, name)
        if not callable(attr):
            return attr

        async def _wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await attr(*args, **kwargs)
            if isinstance(result, dict) and "id" in result and "password_hash" in result:
                return _as_row_obj(result)
            if isinstance(result, list) and result and isinstance(result[0], dict) and "id" in result[0]:
                return [_as_row_obj(item) for item in result]
            return result

        return _wrapper


def get_account_api(db: AsyncSession) -> AccountApi:
    """工厂：返回账户跨上下文端口实现。"""
    return AccountApiAdapter(db)
