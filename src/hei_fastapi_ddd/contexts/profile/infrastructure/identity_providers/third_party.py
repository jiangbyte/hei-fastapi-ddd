"""Author: Charlie

配置驱动的第三方实人认证 Provider 占位实现（httpx HTTP 调用）。
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import httpx

from hei_fastapi_ddd.contexts.profile.application.identity.dto import (
    RealNameCaseCallbackCommand,
    RealNameCaseInitResponse,
    RealNameCaseInitThirdPartyCommand,
)
from hei_fastapi_ddd.contexts.profile.domain.identity.enums import VerifyChannel
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.security.safe_url import UnsafeUrlError, validate_outbound_url
from hei_fastapi_ddd.types.business import BusinessError

logger = logging.getLogger(__name__)


class ThirdPartyIdentityVerifyProvider:
    def provider_code(self) -> str:
        return "THIRD_PARTY"

    def supports(self, verify_channel: str, document_type: str) -> bool:
        return verify_channel.upper() == VerifyChannel.THIRD_PARTY.value

    async def init_verify(
        self,
        case: Mapping[str, Any],
        param: RealNameCaseInitThirdPartyCommand,
    ) -> RealNameCaseInitResponse:
        init_url = (settings.profile_identity.third_party_init_url or "").strip()
        if not init_url:
            raise BusinessError("Third-party identity provider is not configured")

        case_id = str(case["case_id"])
        payload = {
            "case_id": case_id,
            "account_id": case.get("account_id"),
            "document_type": case.get("document_type"),
            "business_type": case.get("business_type"),
            "provider": self.provider_code(),
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        api_key = (settings.profile_identity.third_party_api_key or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        timeout = settings.profile_identity.third_party_timeout_seconds
        try:
            validate_outbound_url(init_url)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                response = await client.post(init_url, json=payload, headers=headers)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except UnsafeUrlError as exc:
            logger.warning("Third-party identity init blocked unsafe url: %s", exc)
            raise BusinessError("Third-party identity provider is not configured") from exc
        except httpx.HTTPError as exc:
            logger.warning("Third-party identity init failed: %s", exc)
            raise BusinessError("Third-party identity provider is not configured") from exc

        provider_order_no = str(
            data.get("provider_order_no") or data.get("order_no") or f"TP-{case_id}"
        )
        redirect_url = data.get("redirect_url") or data.get("redirectUrl")
        provider = str(data.get("provider") or self.provider_code())
        return RealNameCaseInitResponse(
            case_id=case_id,
            provider=provider,
            provider_order_no=provider_order_no,
            redirect_url=str(redirect_url) if redirect_url else None,
        )

    async def handle_callback(
        self,
        case: Mapping[str, Any],
        param: RealNameCaseCallbackCommand,
    ) -> None:
        callback_url = (settings.profile_identity.third_party_callback_url or "").strip()
        if not callback_url:
            return None

        payload = {
            "case_id": case.get("case_id"),
            "provider_order_no": param.provider_order_no or case.get("provider_order_no"),
            "success": param.success,
            "message": param.message,
        }
        headers: dict[str, str] = {"Content-Type": "application/json"}
        api_key = (settings.profile_identity.third_party_api_key or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        timeout = settings.profile_identity.third_party_timeout_seconds
        try:
            validate_outbound_url(callback_url)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                await client.post(callback_url, json=payload, headers=headers)
        except UnsafeUrlError as exc:
            logger.warning("Third-party identity callback blocked unsafe url: %s", exc)
        except httpx.HTTPError as exc:
            logger.warning("Third-party identity callback notify failed: %s", exc)
        return None
