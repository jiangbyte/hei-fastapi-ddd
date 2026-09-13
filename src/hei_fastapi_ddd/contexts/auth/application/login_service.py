""" Author: Charlie

登录、OTP、会话签发/刷新与密码过期提醒。
"""

from __future__ import annotations

import secrets
from uuid import uuid4

from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.redis.keys import (
    login_otp_key,
    password_expiry_notify_key,
)
from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.email.sender import send_templated_mail
from hei_fastapi_ddd.shared.exceptions.business import AuthenticationError, BusinessError
from hei_fastapi_ddd.shared.observability.metrics import record_login_attempt
from hei_fastapi_ddd.shared.security.password import hash_password_async
from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store
from hei_fastapi_ddd.shared.security.token import generate_token
from hei_fastapi_ddd.shared.sms.sender import send_templated_sms
from hei_fastapi_ddd.contexts.auth.application.base import _audit_record, session_expires_in
from hei_fastapi_ddd.contexts.auth.domain.policy import (
    ensure_identity_allowed,
    no_user_policy_for,
)
from hei_fastapi_ddd.contexts.auth.application.protection import login_protection_service
from hei_fastapi_ddd.contexts.auth.interfaces.http.auth_schemas import (
    LoginPayload,
    LoginResponse,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.iam.application.account.password_helper import (
    get_password_age_days,
    is_password_expired,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.account_schemas import (
    AccountCreateRequest,
)
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_repository import ProfileUserPortalRepository
from hei_fastapi_ddd.contexts.profile.interfaces.http.portal_schemas import ProfileUserPortalUpsertPayload
from hei_fastapi_ddd.contexts.sys.application.audit.audit_application_service import OperationAuditService


class LoginMixin:
    """登录、OTP、会话签发/刷新与密码过期提醒。"""

    async def login(self, payload: LoginPayload) -> SessionPayload:
        """执行登录流程并签发会话。"""
        audit_snapshots.subject(payload.account)
        login_mode = (payload.login_mode or "PASSWORD").strip().upper()
        try:
            ensure_identity_allowed(
                payload.account_type,
                payload.identity_type,
                login_mode=login_mode,
            )
            await login_protection_service.ensure_allowed(
                account_type=payload.account_type,
                account=payload.account,
                client_ip=payload.client_ip,
            )
            account = await self.account_repo.get_account_by_identifier(
                payload.account,
                [payload.identity_type],
            )
            if account is None:
                account = await self._maybe_auto_create(payload)
            if login_mode == "OTP":
                await self._verify_login_otp(payload)
                self._validate_account_status(account, payload.account_type)
            else:
                await self._validate_account(account, payload.password or "", payload.account_type)
        except (AuthenticationError, BusinessError):
            await login_protection_service.record_failure(
                account_type=payload.account_type,
                account=payload.account,
                client_ip=payload.client_ip,
            )
            record_login_attempt(payload.account_type.value, "failure", "invalid_credentials")
            await OperationAuditService(self.db).record(
                **_audit_record(
                    module="auth",
                    action="login",
                    resource_type="auth",
                    resource_id=payload.account,
                    success=False,
                    error_message="Invalid or locked login attempt",
                    account_type=payload.account_type.value,
                    operator_name=payload.account,
                    ip=payload.client_ip,
                    user_agent=payload.user_agent,
                )
            )
            raise
        assert account is not None
        return await self._issue_session(account, payload)

    async def send_login_code(
        self,
        *,
        account_type: AccountType,
        channel: str,
        target: str,
        client_ip: str | None = None,
    ) -> None:
        """按渠道发送登录验证码，未绑定且策略不允许自动创建时不泄露用户是否存在。"""
        channel_u = channel.strip().upper()
        identity = (
            AccountIdentityType.EMAIL if channel_u == "EMAIL" else AccountIdentityType.PHONE
        )
        policy = ensure_identity_allowed(account_type, identity, login_mode="OTP")
        normalized = target.strip().lower() if channel_u == "EMAIL" else target.strip()
        account = await self.account_repo.get_account_by_identifier(normalized, [identity])
        if account is None:
            policy_name = no_user_policy_for(policy, identity)
            if policy_name != "AUTO_CREATE":
                # 不泄露用户是否存在
                return
        code = f"{secrets.randbelow(1_000_000):06d}"
        redis = self._required_redis("Redis is required for OTP login")
        ttl = settings.auth.password_reset_token_ttl_seconds
        await redis.setex(login_otp_key(account_type.value, channel_u, normalized), ttl, code)
        variables = {
            "app_name": settings.app.name,
            "code": code,
            "expire_minutes": max(1, ttl // 60),
        }
        if channel_u == "EMAIL":
            await send_templated_mail("LOGIN_CODE", normalized, variables)
        else:
            await send_templated_sms("LOGIN_CODE", normalized, variables)

    async def _verify_login_otp(self, payload: LoginPayload) -> None:
        """校验 OTP 登录验证码，成功后一次性消费。"""
        code = (payload.otp_code or "").strip()
        if not code:
            raise AuthenticationError("Invalid or expired OTP code")
        channel = (
            "EMAIL"
            if payload.identity_type == AccountIdentityType.EMAIL
            else "PHONE"
            if payload.identity_type == AccountIdentityType.PHONE
            else ""
        )
        if not channel:
            raise BusinessError("OTP login requires email or phone")
        normalized = (
            payload.account.strip().lower()
            if channel == "EMAIL"
            else payload.account.strip()
        )
        redis = self._required_redis("Redis is required for OTP login")
        key = login_otp_key(payload.account_type.value, channel, normalized)
        raw = await redis.get(key)
        stored = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if not stored or stored != code:
            raise AuthenticationError("Invalid or expired OTP code")
        await redis.delete(key)

    async def _maybe_auto_create(self, payload: LoginPayload) -> SysAccount | None:
        """当策略允许 AUTO_CREATE 时自动创建账户并返回，否则返回 None。"""
        policy = ensure_identity_allowed(
            payload.account_type,
            payload.identity_type,
            login_mode=payload.login_mode,
        )
        if no_user_policy_for(policy, payload.identity_type) != "AUTO_CREATE":
            return None
        if payload.account_type == AccountType.ADMIN:
            # 管理端默认仍 DENY；仅显式 AUTO_CREATE 才会走到这里
            pass
        identity = payload.account.strip()
        email = identity if payload.identity_type == AccountIdentityType.EMAIL else None
        phone = identity if payload.identity_type == AccountIdentityType.PHONE else None
        account_name = f"u_{uuid4().hex[:10]}"
        default_password = (settings.auth.default_password or secrets.token_urlsafe(12)).strip()
        async with transactional(self.db):
            account = await self.account_repo.create(
                AccountCreateRequest(
                    account=account_name,
                    password=default_password,
                    account_type=payload.account_type,
                    account_status=AccountStatusEnum.ENABLED,
                    email=email,
                    phone=phone,
                    email_login_enabled=bool(email),
                    phone_login_enabled=bool(phone),
                    email_identity_verified=bool(email),
                    phone_identity_verified=bool(phone),
                ),
                password_hash=await hash_password_async(default_password),
            )
            if payload.account_type == AccountType.PORTAL:
                await ProfileUserPortalRepository(self.db).upsert(
                    ProfileUserPortalUpsertPayload(
                        account_id=account.id,
                        name=None,
                        nickname=account_name,
                        phone=phone,
                        email=email,
                        avatar=None,
                        signature=None,
                        bio=None,
                        level=None,
                    ),
                )
            await self._assign_register_defaults(account.id, payload.account_type)
        return account

    async def password_expiry_warning_days(self, account_id: str) -> int | None:
        """返回密码剩余有效天数（仅在临近过期时），否则返回 None。"""
        warning = settings.password_policy.expiry_warning_days
        expire_days = settings.password_policy.expire_days
        if warning <= 0 or expire_days <= 0:
            return None
        age = await get_password_age_days(self.db, account_id)
        if age is None:
            return None
        remaining = expire_days - age
        if 0 < remaining <= warning:
            return int(remaining)
        return None

    async def _issue_session(self, account: SysAccount, payload: LoginPayload) -> SessionPayload:
        """组装会话载荷、写入会话存储并记录审计与指标。"""
        password_expired_ = await is_password_expired(self.db, account.id)
        session_payload = await self.session_service.build_session_payload(
            account,
            generate_token(),
            remember_me=payload.remember_me,
            password_expired=password_expired_,
            client_ip=payload.client_ip,
            user_agent=payload.user_agent,
            device_label=payload.device_label,
        )
        ttl = settings.auth.token_ttl_seconds
        force_bind_email, force_bind_phone = await self._force_bind_flags(
            account, payload.account_type
        )
        session_payload.force_bind_email = force_bind_email
        session_payload.force_bind_phone = force_bind_phone
        await session_store.set(session_payload, ttl_seconds=ttl)
        await session_store.prune_excess_sessions(
            account_type=str(session_payload.account_type),
            account_id=session_payload.account_id,
            max_sessions=settings.auth.max_concurrent_sessions,
        )
        await login_protection_service.record_success(
            account_type=payload.account_type,
            account=payload.account,
            client_ip=payload.client_ip,
        )
        record_login_attempt(payload.account_type.value, "success")
        audit_snapshots.resource_id(account.id)
        await OperationAuditService(self.db).record(
            **_audit_record(
                module="auth",
                action="login",
                resource_type="auth",
                resource_id=account.id,
                success=True,
                account_id=account.id,
                account_type=payload.account_type.value,
                operator_name=payload.account,
                ip=payload.client_ip,
                user_agent=payload.user_agent,
            )
        )
        await self._maybe_notify_password_expiring(account.id)
        return session_payload

    async def issue_oauth_session(
        self,
        account: SysAccount,
        account_type: AccountType,
        *,
        login_label: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
    ) -> LoginResponse:
        """为 OAuth 登录签发会话并返回登录结果（含强制绑定标记）。"""
        password_expired_ = await is_password_expired(self.db, account.id)
        session_payload = await self.session_service.build_session_payload(
            account,
            generate_token(),
            remember_me=True,
            password_expired=password_expired_,
            client_ip=client_ip,
            user_agent=user_agent,
            device_label=device_label,
        )
        force_bind_email, force_bind_phone = await self._force_bind_flags(
            account, account_type
        )
        session_payload.force_bind_email = force_bind_email
        session_payload.force_bind_phone = force_bind_phone
        await session_store.set(
            session_payload, ttl_seconds=settings.auth.token_ttl_seconds
        )
        await session_store.prune_excess_sessions(
            account_type=str(session_payload.account_type),
            account_id=session_payload.account_id,
            max_sessions=settings.auth.max_concurrent_sessions,
        )
        record_login_attempt(account_type.value, "success")
        await OperationAuditService(self.db).record(
            module="auth",
            action="oauth_wechat_mp_login",
            resource_type="auth",
            resource_id=account.id,
            success=True,
            account_id=account.id,
            account_type=account.account_type,
            operator_name=login_label or account.id,
            ip=client_ip,
            user_agent=user_agent,
        )
        await self._maybe_notify_password_expiring(account.id)
        return LoginResponse(
            token=session_payload.token,
            account_id=account.id,
            account_type=account_type,
            password_expired=password_expired_,
            password_expiry_warning_days=await self.password_expiry_warning_days(
                account.id
            ),
            expires_in=session_expires_in(session_payload),
            force_bind_email=session_payload.force_bind_email,
            force_bind_phone=session_payload.force_bind_phone,
        )

    async def _force_bind_flags(
        self, account: SysAccount, account_type: AccountType
    ) -> tuple[bool, bool]:
        """按 AUTH_FORCE_BIND_{TYPE}_{EMAIL|PHONE} 配置与账号已绑定身份计算强制绑定标记。"""
        type_name = account_type.value
        force_email = config_reader.get_bool(
            f"AUTH_FORCE_BIND_{type_name}_EMAIL", False
        ) and not await self.account_repo.has_identity(account.id, AccountIdentityType.EMAIL)
        force_phone = config_reader.get_bool(
            f"AUTH_FORCE_BIND_{type_name}_PHONE", False
        ) and not await self.account_repo.has_identity(account.id, AccountIdentityType.PHONE)
        return bool(force_email), bool(force_phone)

    async def force_bind_identity_flag(
        self, account_id: str, account_type: AccountType
    ) -> bool:
        """按 AUTH_FORCE_BIND_{TYPE}_IDENTITY 与实名状态计算强制实名标记。"""
        type_name = account_type.value
        if not config_reader.get_bool(f"AUTH_FORCE_BIND_{type_name}_IDENTITY", False):
            return False
        from hei_fastapi_ddd.contexts.profile.application.identity.identity_application_service import ProfileIdentityService

        return not await ProfileIdentityService(self.db).is_verified(account_id)

    async def refresh_session(
        self, token: str, account_type: AccountType
    ) -> LoginResponse:
        """刷新当前会话（滑动 TTL、重算授权）并返回最新登录结果，会话失效时抛错。"""
        session = await session_store.get(token)
        if session is None:
            raise AuthenticationError("Session expired or invalid")
        if str(session.account_type) != account_type.value:
            raise BusinessError("账号类型不匹配")
        account = await self.account_repo.get_required(session.account_id)
        authorization = await self.relation_repo.get_account_authorization(account.id)
        password_expired_ = await is_password_expired(self.db, account.id)
        session_payload = self.session_service._build_session_payload_from_authorization(
            account,
            token,
            authorization,
            remember_me=session.remember_me,
            password_expired=password_expired_,
            client_ip=session.client_ip,
            user_agent=session.user_agent,
            device_label=session.device_label,
        )
        force_bind_email, force_bind_phone = await self._force_bind_flags(
            account, account_type
        )
        session_payload.force_bind_email = force_bind_email
        session_payload.force_bind_phone = force_bind_phone
        await session_store.set(
            session_payload, ttl_seconds=settings.auth.token_ttl_seconds
        )
        await self._maybe_notify_password_expiring(account.id)
        return LoginResponse(
            token=session_payload.token,
            account_id=session_payload.account_id,
            account_type=account_type,
            password_expired=session_payload.password_expired,
            password_expiry_warning_days=await self.password_expiry_warning_days(
                session.account_id
            ),
            expires_in=session_expires_in(session_payload),
            force_bind_email=force_bind_email,
            force_bind_phone=force_bind_phone,
        )

    async def _maybe_notify_password_expiring(self, account_id: str) -> None:
        """密码临近过期时发送邮件/短信提醒（24h 内仅一次，对齐 hei-boot）。"""
        warning_days = await self.password_expiry_warning_days(account_id)
        if not warning_days:
            return
        if not await self._try_mark_password_expiry_notified(account_id):
            return
        account_name = account_id
        email_ident: str | None = None
        phone_ident: str | None = None
        for item in await self.account_repo.list_identities_by_account_ids([account_id]):
            if (
                item.identity_type == AccountIdentityType.ACCOUNT.value
                and item.bind_status == "BOUND"
                and item.identifier
            ):
                account_name = item.identifier
            elif (
                item.identity_type == AccountIdentityType.EMAIL.value
                and item.bind_status == "BOUND"
                and item.identifier
            ):
                email_ident = item.identifier
            elif (
                item.identity_type == AccountIdentityType.PHONE.value
                and item.bind_status == "BOUND"
                and item.identifier
            ):
                phone_ident = item.identifier
        variables = {
            "app_name": settings.app.name,
            "account": account_name,
            "remaining_days": str(warning_days),
        }
        if email_ident:
            await send_templated_mail("PASSWORD_EXPIRING", email_ident, variables)
        if phone_ident:
            await send_templated_sms("PASSWORD_EXPIRING", phone_ident, variables)

    async def _try_mark_password_expiry_notified(self, account_id: str) -> bool:
        """24h 内仅通知一次密码即将过期。"""
        redis = get_redis()
        if redis is None:
            return True
        try:
            return bool(
                await redis.set(password_expiry_notify_key(account_id), "1", nx=True, ex=86400)
            )
        except Exception:
            return True
