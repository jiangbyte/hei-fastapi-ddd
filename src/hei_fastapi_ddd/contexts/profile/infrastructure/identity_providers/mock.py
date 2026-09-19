"""Author: Charlie

Mock 第三方实人认证 Provider（开发/测试用，对齐 hei-boot）。
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from hei_fastapi_ddd.contexts.profile.application.identity.dto import (
    RealNameCaseCallbackCommand,
    RealNameCaseInitResponse,
    RealNameCaseInitThirdPartyCommand,
)
from hei_fastapi_ddd.contexts.profile.domain.identity.enums import VerifyChannel


class MockIdentityVerifyProvider:
    def provider_code(self) -> str:
        return "MOCK"

    def supports(self, verify_channel: str, document_type: str) -> bool:
        return verify_channel.upper() == VerifyChannel.THIRD_PARTY.value

    async def init_verify(
        self,
        case: Mapping[str, Any],
        param: RealNameCaseInitThirdPartyCommand,
    ) -> RealNameCaseInitResponse:
        case_id = str(case["case_id"])
        return RealNameCaseInitResponse(
            case_id=case_id,
            provider=self.provider_code(),
            provider_order_no=f"MOCK-{uuid.uuid4().hex}",
            redirect_url=f"/mock/identity-verify?case_id={case_id}",
        )

    async def handle_callback(
        self,
        case: Mapping[str, Any],
        param: RealNameCaseCallbackCommand,
    ) -> None:
        # 回调结果由 RealNameCaseService 统一处理状态流转
        return None
