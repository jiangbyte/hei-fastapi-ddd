"""Author: Charlie

第三方实人认证 Provider 协议。
"""

from typing import Protocol

from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_po import RealNameCase
from hei_fastapi_ddd.contexts.profile.interfaces.http.identity_schemas import (
    RealNameCaseCallbackRequest,
    RealNameCaseInitResponse,
    RealNameCaseInitThirdPartyRequest,
)


class IdentityVerifyProvider(Protocol):
    def provider_code(self) -> str: ...

    def supports(self, verify_channel: str, document_type: str) -> bool: ...

    async def init_verify(
        self,
        case: RealNameCase,
        param: RealNameCaseInitThirdPartyRequest,
    ) -> RealNameCaseInitResponse: ...

    async def handle_callback(
        self,
        case: RealNameCase,
        param: RealNameCaseCallbackRequest,
    ) -> None: ...
