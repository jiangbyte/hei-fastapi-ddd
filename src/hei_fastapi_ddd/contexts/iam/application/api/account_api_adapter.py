""" Author: Charlie

AccountApi 适配器：用基础设施仓储实现跨上下文端口。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.api.account_api import AccountApi
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import (
    AccountRepository,
)


class AccountApiAdapter:
    """将 AccountRepository 适配为 AccountApi，供 auth 等上下文注入。"""

    def __init__(self, db: AsyncSession):
        self._repo = AccountRepository(db)

    async def get_account_by_id(self, account_id: str) -> Any | None:
        return await self._repo.get_account_by_id(account_id)

    async def get_account_by_identifier(
        self,
        identifier: str,
        identity_types: list[Any] | None = None,
    ) -> Any | None:
        return await self._repo.get_account_by_identifier(
            identifier,
            identity_types=identity_types,
        )

    async def create_account(self, *args: Any, **kwargs: Any) -> Any:
        return await self._repo.create(*args, **kwargs)

    async def get_required(self, account_id: str) -> Any:
        return await self._repo.get_required(account_id)

    def __getattr__(self, name: str) -> Any:
        """过渡期转发仓储扩展方法，避免 auth 直连 infrastructure 包。"""
        return getattr(self._repo, name)

    @property
    def repo(self) -> AccountRepository:
        """过渡期暴露完整仓储（会话/登录等仍需扩展方法）。"""
        return self._repo


def get_account_api(db: AsyncSession) -> AccountApi:
    """工厂：返回账户跨上下文端口实现。"""
    return AccountApiAdapter(db)
