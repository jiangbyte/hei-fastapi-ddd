"""Author: Charlie

按 provider code 或通道路由 IdentityVerifyProvider（对齐 hei-boot）。
"""

from __future__ import annotations

from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.contexts.profile.infrastructure.identity_providers.base import IdentityVerifyProvider
from hei_fastapi_ddd.contexts.profile.infrastructure.identity_providers.mock import MockIdentityVerifyProvider
from hei_fastapi_ddd.contexts.profile.infrastructure.identity_providers.third_party import ThirdPartyIdentityVerifyProvider


class IdentityVerifyProviderRegistry:
    def __init__(self) -> None:
        self._providers: list[IdentityVerifyProvider] = [
            ThirdPartyIdentityVerifyProvider(),
            MockIdentityVerifyProvider(),
        ]

    def resolve(
        self,
        verify_channel: str,
        document_type: str,
        preferred_provider: str | None,
    ) -> IdentityVerifyProvider:
        if preferred_provider and preferred_provider.strip():
            code = preferred_provider.strip().upper()
            for provider in self._providers:
                if provider.provider_code().upper() == code:
                    return provider
            raise BusinessError(f"Unsupported identity provider: {preferred_provider}")

        for provider in self._providers:
            if provider.provider_code() == "MOCK":
                continue
            if provider.supports(verify_channel, document_type):
                return provider

        for provider in self._providers:
            if provider.supports(verify_channel, document_type):
                return provider

        raise BusinessError(f"No identity provider for channel={verify_channel}")


_provider_registry: IdentityVerifyProviderRegistry | None = None


def get_provider_registry() -> IdentityVerifyProviderRegistry:
    global _provider_registry
    if _provider_registry is None:
        _provider_registry = IdentityVerifyProviderRegistry()
    return _provider_registry
