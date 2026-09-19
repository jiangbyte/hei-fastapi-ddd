"""Author: Charlie

IdentityVerifyProviderRegistryPort 适配器。
"""

from __future__ import annotations

from hei_fastapi_ddd.contexts.profile.domain.identity.ports import (
    IdentityVerifyProviderRegistryPort,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.identity_providers.registry import (
    get_provider_registry,
)


class IdentityVerifyProviderRegistryAdapter:
    def __init__(self) -> None:
        self._registry = get_provider_registry()

    def resolve(
        self, verify_channel: str, document_type: str, provider: str | None
    ):
        return self._registry.resolve(verify_channel, document_type, provider)


def get_identity_provider_registry_port() -> IdentityVerifyProviderRegistryPort:
    return IdentityVerifyProviderRegistryAdapter()
