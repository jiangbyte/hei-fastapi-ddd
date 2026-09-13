""" Author: Charlie

邮箱/手机密码找回与重置。
"""

from __future__ import annotations

import json
import secrets
from urllib.parse import urlencode

from hei_fastapi_ddd.contexts.auth.application.base import _PASSWORD_RESET_URL_KEYS, _audit_record
from hei_fastapi_ddd.contexts.auth.interfaces.http.auth_schemas import (
    ForgotPasswordByPhoneRequest,
    ForgotPasswordRequest,
    ResetPasswordByPhoneRequest,
    ResetPasswordRequest,
)
from hei_fastapi_ddd.contexts.iam.application.account.password_helper import (
    validate_and_record_password,
)
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.contexts.sys.application.audit.audit_application_service import (
    OperationAuditService,
)
from hei_fastapi_ddd.contexts.sys.application.audit.support import resolve_account_login
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.email.sender import send_templated_mail
from hei_fastapi_ddd.shared.exceptions.business import AuthenticationError, BusinessError
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.redis.keys import (
    password_reset_token_key,
    reset_password_otp_key,
)
from hei_fastapi_ddd.shared.security.password import hash_password_async, verify_password_async
from hei_fastapi_ddd.shared.security.token import generate_token
from hei_fastapi_ddd.shared.sms.sender import send_templated_sms


class PasswordResetMixin:
    """邮箱/手机密码找回与重置。"""

    async def forgot_password(
        self,
        payload: ForgotPasswordRequest,
        account_type: AccountType,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """处理忘记密码：校验账户后生成重置链接并发送邮件。"""
        email = payload.email.strip().lower()
        audit_snapshots.subject(email)
        account = await self.account_repo.get_account_by_identifier(
            email,
            [AccountIdentityType.EMAIL],
        )
        if account is None or account.account_type != account_type.value:
            await self._record_password_reset_request(
                account_type,
                email,
                False,
                client_ip,
                user_agent,
            )
            return
        try:
            self._validate_account_status(account, account_type)
        except AuthenticationError:
            await self._record_password_reset_request(
                account_type,
                email,
                False,
                client_ip,
                user_agent,
            )
            return

        reset_token = generate_token()
        redis = self._required_redis("Redis is required for password reset")
        await redis.setex(
            password_reset_token_key(reset_token),
            settings.auth.password_reset_token_ttl_seconds,
            json.dumps(
                {
                    "account_id": account.id,
                    "account_type": account_type.value,
                    "email": email,
                    "token_hash": await hash_password_async(reset_token),
                }
            ),
        )
        reset_link = self._build_password_reset_link(account_type, reset_token)
        expire_minutes = settings.auth.password_reset_token_ttl_seconds // 60
        await send_templated_mail(
            "RESET_PASSWORD_CODE",
            email,
            {
                "app_name": settings.app.name,
                "reset_link": reset_link,
                "email": email,
                "expire_minutes": expire_minutes,
            },
        )
        await self._record_password_reset_request(
            account_type,
            email,
            True,
            client_ip,
            user_agent,
            account.id,
        )

    async def reset_password(
        self,
        payload: ResetPasswordRequest,
        account_type: AccountType,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """校验重置 token 并更新账户密码，随后清理会话。"""
        key = password_reset_token_key(payload.token)
        redis = self._required_redis("Redis is required for password reset")
        raw = await redis.get(key)
        raw_text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if not raw_text:
            raise AuthenticationError("Invalid or expired reset link")
        data = json.loads(raw_text)
        # 身份只绑定在 token→Redis 载荷上，禁止把邮箱放进重置链接或要求客户端回传
        if (
            not data.get("account_id")
            or data.get("account_type") != account_type.value
            or not await verify_password_async(payload.token, data["token_hash"])
        ):
            raise AuthenticationError("Invalid or expired reset link")

        account = await self.account_repo.get_required(str(data["account_id"]))
        self._validate_account_status(account, account_type)
        account_name = await resolve_account_login(self.db, account.id) or account.id
        audit_snapshots.before_entity(account)
        audit_snapshots.subject(account_name)
        async with transactional(self.db):
            await validate_and_record_password(
                self.db,
                account.id,
                payload.password,
                changed_by=account.id,
                change_reason="self_reset",
                account=account,
            )
            await self.account_repo.update_password_hash(
                account.id, await hash_password_async(payload.password)
            )
        updated = await self.account_repo.get_required(account.id)
        audit_snapshots.after_entity(updated)
        await redis.delete(key)
        await self.session_service.delete_account_sessions(account.account_type, account.id)
        await OperationAuditService(self.db).record(
            **_audit_record(
                module="auth",
                action="reset_password",
                resource_type="auth",
                resource_id=account.id,
                success=True,
                account_id=account.id,
                account_type=account.account_type,
                ip=client_ip,
                user_agent=user_agent,
            )
        )

    async def forgot_password_by_phone(
        self,
        payload: ForgotPasswordByPhoneRequest,
        account_type: AccountType,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """通过手机找回密码：校验账户后发送重置 OTP。"""
        phone = payload.phone.strip()
        audit_snapshots.subject(phone)
        account = await self.account_repo.get_account_by_identifier(
            phone, [AccountIdentityType.PHONE]
        )
        if account is None or account.account_type != account_type.value:
            return
        try:
            self._validate_account_status(account, account_type)
        except AuthenticationError:
            return

        code = f"{secrets.randbelow(1_000_000):06d}"
        redis = self._required_redis("Redis is required for password reset")
        ttl = settings.auth.password_reset_token_ttl_seconds
        await redis.setex(reset_password_otp_key(account_type.value, phone), ttl, code)
        variables = {
            "app_name": settings.app.name,
            "code": code,
            "expire_minutes": max(1, ttl // 60),
        }
        await send_templated_sms("RESET_PASSWORD_CODE", phone, variables)
        await OperationAuditService(self.db).record(
            **_audit_record(
                module="auth",
                action="forgot_password_phone",
                resource_type="auth",
                resource_id=account.id,
                success=True,
                account_id=account.id,
                account_type=account.account_type,
                ip=client_ip,
                user_agent=user_agent,
            )
        )

    async def reset_password_by_phone(
        self,
        payload: ResetPasswordByPhoneRequest,
        account_type: AccountType,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """校验手机 OTP 并更新账户密码。"""
        phone = payload.phone.strip()
        otp = (payload.otp_code or "").strip()
        redis = self._required_redis("Redis is required for password reset")
        key = reset_password_otp_key(account_type.value, phone)
        stored = await redis.get(key)
        stored_text = stored.decode("utf-8") if isinstance(stored, bytes) else stored
        if not stored_text or stored_text != otp:
            raise AuthenticationError("Invalid or expired verification code")

        account = await self.account_repo.get_account_by_identifier(
            phone, [AccountIdentityType.PHONE]
        )
        if account is None or account.account_type != account_type.value:
            raise AuthenticationError("Account not found")
        self._validate_account_status(account, account_type)
        account_name = await resolve_account_login(self.db, account.id) or account.id
        audit_snapshots.before_entity(account)
        audit_snapshots.subject(account_name)

        async with transactional(self.db):
            await validate_and_record_password(
                self.db,
                account.id,
                payload.password,
                changed_by=account.id,
                change_reason="self_reset_phone",
                account=account,
            )
            await self.account_repo.update_password_hash(
                account.id, await hash_password_async(payload.password)
            )
        updated = await self.account_repo.get_required(account.id)
        audit_snapshots.after_entity(updated)
        await redis.delete(key)
        await self.session_service.delete_account_sessions(account.account_type, account.id)
        await OperationAuditService(self.db).record(
            **_audit_record(
                module="auth",
                action="reset_password_phone",
                resource_type="auth",
                resource_id=account.id,
                success=True,
                account_id=account.id,
                account_type=account.account_type,
                ip=client_ip,
                user_agent=user_agent,
            )
        )

    def _build_password_reset_link(self, account_type: AccountType, token: str) -> str:
        """根据账户类型读取配置的模板地址并拼接 token 生成重置链接。"""
        config_key = _PASSWORD_RESET_URL_KEYS.get(account_type)
        if not config_key:
            raise BusinessError(f"Unsupported account type for password reset: {account_type}")
        base_url = (config_reader.get(config_key) or "").strip()
        if not base_url:
            raise BusinessError(f"Missing sys_config: {config_key}")
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}{urlencode({'token': token})}"

    async def _record_password_reset_request(
        self,
        account_type: AccountType,
        email: str,
        success: bool,
        client_ip: str | None,
        user_agent: str | None,
        account_id: str | None = None,
    ) -> None:
        """记录密码重置请求的审计日志。"""
        await OperationAuditService(self.db).record(
            **_audit_record(
                module="auth",
                action="forgot_password",
                resource_type="auth",
                resource_id=account_id or email,
                success=success,
                account_id=account_id,
                account_type=account_type.value,
                ip=client_ip,
                user_agent=user_agent,
            )
        )
