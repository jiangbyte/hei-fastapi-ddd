"""Author: Charlie

Mock 第三方实人认证 Provider（开发/测试用，对齐 hei-boot）。
"""

from __future__ import annotations

import uuid

from hei_fastapi_ddd.contexts.profile.domain.identity.enums import VerifyChannel
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_po import RealNameCase
from hei_fastapi_ddd.contexts.profile.interfaces.http.identity_schemas import (
    RealNameCaseCallbackRequest,
    RealNameCaseInitResponse,
    RealNameCaseInitThirdPartyRequest,
)


class MockIdentityVerifyProvider:
    def provider_code(self) -> str:
        return "MOCK"

    def supports(self, verify_channel: str, document_type: str) -> bool:
        return verify_channel.upper() == VerifyChannel.THIRD_PARTY.value

    async def init_verify(
        self,
        case: RealNameCase,
        param: RealNameCaseInitThirdPartyRequest,
    ) -> RealNameCaseInitResponse:
        return RealNameCaseInitResponse(
            case_id=case.case_id,
            provider=self.provider_code(),
            provider_order_no=f"MOCK-{uuid.uuid4().hex}",
            redirect_url=f"/mock/identity-verify?case_id={case.case_id}",
        )

    async def handle_callback(
        self,
        case: RealNameCase,
        param: RealNameCaseCallbackRequest,
    ) -> None:
        # 回调结果由 RealNameCaseService 统一处理状态流转
        return None
