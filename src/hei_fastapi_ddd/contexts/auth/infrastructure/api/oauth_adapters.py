"""Author: Charlie

OAuth 端口适配器：委托 auth 基础设施实现。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.auth.application.api.oauth_ports import (
    OauthBindingRepositoryPort,
    OauthClientPort,
    OauthExchangeStorePort,
    OauthStatePayload,
    OauthStateStorePort,
)
from hei_fastapi_ddd.contexts.auth.domain.oauth.provider import OauthProvider, OauthUserProfile
from hei_fastapi_ddd.contexts.auth.infrastructure.oauth.client import OauthClientFacade
from hei_fastapi_ddd.contexts.auth.infrastructure.oauth.stores import (
    OauthExchangeStore,
    OauthStateStore,
)
from hei_fastapi_ddd.contexts.auth.infrastructure.persistence.oauth_repository import (
    AccountOauthBindingRepository,
)
from hei_fastapi_ddd.shared.config.enums import AccountType


def _row(entity: Any) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class OauthClientAdapter:
    def __init__(self) -> None:
        self._client = OauthClientFacade()

    async def ensure_enabled(self, account_type: AccountType, provider: OauthProvider) -> None:
        await self._client.ensure_enabled(account_type, provider)

    def build_authorize_url(
        self, account_type: AccountType, provider: OauthProvider, state: str
    ) -> str:
        return self._client.build_authorize_url(account_type, provider, state)

    async def login_by_code(
        self,
        account_type: AccountType,
        provider: OauthProvider,
        code: str | None,
        state: str | None,
    ) -> OauthUserProfile:
        return await self._client.login_by_code(account_type, provider, code, state)

    async def login_wechat_mp(
        self, account_type: AccountType, code: str | None
    ) -> OauthUserProfile:
        return await self._client.login_wechat_mp(account_type, code)


class OauthStateStoreAdapter:
    def __init__(self) -> None:
        self._store = OauthStateStore()

    async def save(self, payload: OauthStatePayload) -> str:
        return await self._store.save(payload)

    async def consume(self, state: str | None) -> OauthStatePayload | None:
        return await self._store.consume(state)


class OauthExchangeStoreAdapter:
    def __init__(self) -> None:
        self._store = OauthExchangeStore()

    async def save(self, login_result: Mapping[str, Any]) -> str:
        return await self._store.save(dict(login_result))

    async def consume(self, code: str | None) -> dict[str, Any]:
        return await self._store.consume(code)


class OauthBindingRepositoryAdapter:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = AccountOauthBindingRepository(db)

    async def find_by_provider_open_id(
        self, provider: str, open_id: str
    ) -> dict[str, Any] | None:
        row = await self._repo.find_by_provider_open_id(provider, open_id)
        return _row(row) if row is not None else None

    async def find_by_wechat_union_id(self, union_id: str) -> dict[str, Any] | None:
        row = await self._repo.find_by_wechat_union_id(union_id)
        return _row(row) if row is not None else None

    async def list_by_account(self, account_id: str) -> list[dict[str, Any]]:
        return [_row(item) for item in await self._repo.list_by_account(account_id)]

    async def upsert_binding(
        self,
        account_id: str,
        provider: str,
        open_id: str,
        union_id: str | None,
        nickname: str | None,
        avatar: str | None,
        raw_profile_json: str,
    ) -> None:
        await self._repo.upsert_binding(
            account_id,
            provider,
            open_id,
            union_id,
            nickname,
            avatar,
            raw_profile_json,
        )

    async def unbind(self, account_id: str, provider: str) -> None:
        await self._repo.unbind(account_id, provider)


def get_oauth_client_port() -> OauthClientPort:
    return OauthClientAdapter()


def get_oauth_state_store_port() -> OauthStateStorePort:
    return OauthStateStoreAdapter()


def get_oauth_exchange_store_port() -> OauthExchangeStorePort:
    return OauthExchangeStoreAdapter()


def get_oauth_binding_repository_port(db: AsyncSession) -> OauthBindingRepositoryPort:
    return OauthBindingRepositoryAdapter(db)
