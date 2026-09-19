"""Author: Charlie

第三方实人认证 Provider 协议（基础设施实现侧）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from hei_fastapi_ddd.contexts.profile.application.identity.dto import (
    RealNameCaseCallbackCommand,
    RealNameCaseInitResponse,
    RealNameCaseInitThirdPartyCommand,
)


class IdentityVerifyProvider(Protocol):
    def provider_code(self) -> str: ...

    def supports(self, verify_channel: str, document_type: str) -> bool: ...

    async def init_verify(
        self,
        case: Mapping[str, Any],
        param: RealNameCaseInitThirdPartyCommand,
    ) -> RealNameCaseInitResponse: ...

    async def handle_callback(
        self,
        case: Mapping[str, Any],
        param: RealNameCaseCallbackCommand,
    ) -> None: ...
