""" Author: Charlie

自助改密验证：OLD_PASSWORD / EMAIL_CODE / PHONE_CODE。
"""

from __future__ import annotations

import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from collections.abc import Mapping

from hei_fastapi_ddd.contexts.iam.application.api.account_api import AccountApi
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.email.sender import send_templated_mail
from hei_fastapi_ddd.shared.redis.keys import change_password_otp_key
from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.shared.security.password import verify_password_async
from hei_fastapi_ddd.shared.sms.sender import send_templated_sms
from hei_fastapi_ddd.types.business import BusinessError


def change_verify_method() -> str:
    """读取配置的改密验证方式（默认 OLD_PASSWORD）。"""
    return (config_reader.get("PASSWORD_CHANGE_VERIFY_METHOD") or "OLD_PASSWORD").strip().upper()


async def send_change_password_code(
    db: AsyncSession,
    *,
    account_api: AccountApi,
    account: Mapping[str, str],
    account_type: AccountType,
) -> None:
    """按配置的验证方式发送邮箱/短信验证码。"""
    method = change_verify_method()
    if method not in {"EMAIL_CODE", "PHONE_CODE"}:
        raise BusinessError("Current password change method does not use verification code")
    identity_type = (
        AccountIdentityType.EMAIL if method == "EMAIL_CODE" else AccountIdentityType.PHONE
    )
    identities = await account_api.list_identities_by_account_ids([account["id"]])
    target = next(
        (item.get("identifier") for item in identities if item.get("identity_type") == identity_type.value),
        None,
    )
    if not target:
        raise BusinessError("Account has no bound contact for verification")
    code = f"{secrets.randbelow(1_000_000):06d}"
    redis = get_redis()
    if redis is None:
        raise BusinessError("Redis is required for password change verification")
    channel = "EMAIL" if method == "EMAIL_CODE" else "PHONE"
    ttl = settings.auth.password_reset_token_ttl_seconds
    await redis.setex(
        change_password_otp_key(account_type.value, channel, account["id"]),
        ttl,
        code,
    )
    variables = {
        "app_name": settings.app.name,
        "code": code,
        "expire_minutes": max(1, ttl // 60),
    }
    if channel == "EMAIL":
        await send_templated_mail("CHANGE_PASSWORD_CODE", target, variables)
    else:
        await send_templated_sms("CHANGE_PASSWORD_CODE", target, variables)


async def verify_change_password(
    db: AsyncSession,
    *,
    account: Mapping[str, str],
    account_type: AccountType,
    old_password: str | None,
    otp_code: str | None,
) -> None:
    """根据配置的验证方式校验旧密码或验证码。"""
    method = change_verify_method()
    if method == "OLD_PASSWORD":
        if not old_password or not await verify_password_async(old_password, account["password_hash"]):
            raise BusinessError("Old password is incorrect")
        return
    if method in {"EMAIL_CODE", "PHONE_CODE"}:
        code = (otp_code or "").strip()
        if not code:
            raise BusinessError("Verification code is required")
        redis = get_redis()
        if redis is None:
            raise BusinessError("Redis is required for password change verification")
        channel = "EMAIL" if method == "EMAIL_CODE" else "PHONE"
        key = change_password_otp_key(account_type.value, channel, account["id"])
        raw = await redis.get(key)
        stored = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if not stored or stored != code:
            raise BusinessError("Invalid or expired verification code")
        await redis.delete(key)
        return
    raise BusinessError(f"Unsupported password change verify method: {method}")
