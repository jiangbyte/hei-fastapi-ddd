""" Author: Charlie

邮箱/手机绑定验证码发送与消费。
"""

from __future__ import annotations

import secrets

from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.email.sender import send_templated_mail
from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.redis.keys import (
    bind_otp_key,
)
from hei_fastapi_ddd.shared.sms.sender import send_templated_sms


class BindCodeMixin:
    """邮箱/手机绑定验证码发送与消费。"""

    async def send_bind_code(
        self,
        *,
        account_type: AccountType,
        channel: str,
        target: str,
        account_id: str,
    ) -> None:
        """向待绑定邮箱/手机发送验证码，目标已被其他账号占用时拒绝。"""
        channel_u = channel.strip().upper()
        if channel_u not in {"EMAIL", "PHONE"}:
            raise BusinessError("Unsupported bind channel")
        identity_type = (
            AccountIdentityType.EMAIL
            if channel_u == "EMAIL"
            else AccountIdentityType.PHONE
        )
        normalized = (
            target.strip().lower() if channel_u == "EMAIL" else target.strip()
        )
        if not normalized:
            raise BusinessError("Target is required")
        other = await self.account_repo.get_account_by_identifier(
            normalized, [identity_type]
        )
        if other is not None and other.id != account_id:
            raise BusinessError(
                "邮箱已被使用" if channel_u == "EMAIL" else "手机号已被使用"
            )
        code = f"{secrets.randbelow(1_000_000):06d}"
        redis = self._required_redis("Redis is required for bind verification")
        ttl = settings.auth.password_reset_token_ttl_seconds
        await redis.setex(
            bind_otp_key(account_type.value, channel_u, account_id),
            ttl,
            code,
        )
        variables = {
            "app_name": settings.app.name,
            "code": code,
            "expire_minutes": max(1, ttl // 60),
        }
        if channel_u == "EMAIL":
            await send_templated_mail("BIND_EMAIL_CODE", normalized, variables)
        else:
            await send_templated_sms("BIND_PHONE_CODE", normalized, variables)

    async def consume_bind_code(
        self,
        *,
        account_type: AccountType,
        channel: str,
        account_id: str,
        target: str,
        code: str | None,
    ) -> None:
        """校验并一次性消费绑定验证码（未提供或无效时抛错）。"""
        code_value = (code or "").strip()
        if not code_value:
            raise BusinessError("验证码不能为空")
        channel_u = channel.strip().upper()
        redis = self._required_redis("Redis is required for bind verification")
        key = bind_otp_key(account_type.value, channel_u, account_id)
        raw = await redis.get(key)
        stored = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if not stored or stored != code_value:
            raise BusinessError("验证码无效或已过期")
        await redis.delete(key)
