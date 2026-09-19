"""Author: Charlie

OAuth 基础设施端口（应用层依赖协议，由 auth 基础设施装配）。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from hei_fastapi_ddd.contexts.auth.domain.oauth.provider import OauthProvider, OauthUserProfile
from hei_fastapi_ddd.shared.config.enums import AccountType


@dataclass(slots=True)
class OauthStatePayload:
    """OAuth state 存储载荷。"""

    account_type: str
    intent: str
    provider: str
    redirect: str | None = None
    account_id: str | None = None


class OauthClientPort(Protocol):
    """三方 OAuth 客户端。"""

    async def ensure_enabled(self, account_type: AccountType, provider: OauthProvider) -> None:
        ...

    def build_authorize_url(
        self, account_type: AccountType, provider: OauthProvider, state: str
    ) -> str:
        ...

    async def login_by_code(
        self,
        account_type: AccountType,
        provider: OauthProvider,
        code: str | None,
        state: str | None,
    ) -> OauthUserProfile:
        ...

    async def login_wechat_mp(
        self, account_type: AccountType, code: str | None
    ) -> OauthUserProfile:
        ...


class OauthStateStorePort(Protocol):
    async def save(self, payload: OauthStatePayload) -> str:
        ...

    async def consume(self, state: str | None) -> OauthStatePayload | None:
        ...


class OauthExchangeStorePort(Protocol):
    async def save(self, login_result: Mapping[str, Any]) -> str:
        ...

    async def consume(self, code: str | None) -> dict[str, Any]:
        ...


class OauthBindingRepositoryPort(Protocol):
    """账号三方绑定仓储。"""

    async def find_by_provider_open_id(
        self, provider: str, open_id: str
    ) -> dict[str, Any] | None:
        ...

    async def find_by_wechat_union_id(self, union_id: str) -> dict[str, Any] | None:
        ...

    async def list_by_account(self, account_id: str) -> list[dict[str, Any]]:
        ...

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
        ...

    async def unbind(self, account_id: str, provider: str) -> None:
        ...
