""" Author: Charlie

门户注册及注册验证码。
"""

from __future__ import annotations

import secrets
from uuid import uuid4

from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.redis.keys import (
    register_otp_key,
)
from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.email.sender import send_templated_mail
from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.security.account_login import require_account_login, sanitize_account_base
from hei_fastapi_ddd.shared.security.password import hash_password_async
from hei_fastapi_ddd.shared.sms.sender import send_templated_sms
from hei_fastapi_ddd.contexts.auth.application.base import _audit_record
from hei_fastapi_ddd.contexts.auth.domain.policy import (
    get_register_policy,
)
from hei_fastapi_ddd.contexts.auth.interfaces.http.auth_schemas import (
    RegisterRequest,
    RegisterResponse,
)
from hei_fastapi_ddd.contexts.iam.application.account.password_helper import (
    validate_and_record_password,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.account_schemas import (
    AccountCreateRequest,
    AccountDeptAssignRequest,
    AccountRoleAssignRequest,
)
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_repository import ProfileUserPortalRepository
from hei_fastapi_ddd.contexts.profile.interfaces.http.portal_schemas import ProfileUserPortalUpsertPayload
from hei_fastapi_ddd.contexts.sys.application.audit.audit_application_service import OperationAuditService


class RegisterMixin:
    """门户注册及注册验证码。"""

    async def send_register_code(self, *, channel: str, target: str) -> None:
        """发送门户注册通道（邮箱/手机）验证码。"""
        from hei_fastapi_ddd.contexts.auth.domain.policy import get_register_policy

        policy = get_register_policy(AccountType.PORTAL)
        if not policy.enabled:
            raise BusinessError("门户注册已关闭")
        channel_u = channel.strip().upper()
        if channel_u not in {"EMAIL", "PHONE"}:
            raise BusinessError("Unsupported register channel")
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
        if await self.account_repo.get_account_by_identifier(
            normalized, [identity_type]
        ) is not None:
            raise BusinessError(
                "邮箱已被使用" if channel_u == "EMAIL" else "手机号已被使用"
            )
        code = f"{secrets.randbelow(1_000_000):06d}"
        redis = self._required_redis("Redis is required for register verification")
        ttl = settings.auth.password_reset_token_ttl_seconds
        await redis.setex(register_otp_key(channel_u, normalized), ttl, code)
        variables = {
            "app_name": settings.app.name,
            "code": code,
            "expire_minutes": max(1, ttl // 60),
        }
        if channel_u == "EMAIL":
            # 与 hei-boot 一致：注册验证码复用 LOGIN_CODE 模板场景
            await send_templated_mail("LOGIN_CODE", normalized, variables)
        else:
            await send_templated_sms("LOGIN_CODE", normalized, variables)

    async def consume_register_code(
        self, *, channel: str, target: str, code: str | None
    ) -> None:
        """校验并一次性消费注册通道验证码。"""
        code_value = (code or "").strip()
        if not code_value:
            raise BusinessError("验证码不能为空")
        channel_u = channel.strip().upper()
        normalized = (
            target.strip().lower() if channel_u == "EMAIL" else target.strip()
        )
        redis = self._required_redis("Redis is required for register verification")
        key = register_otp_key(channel_u, normalized)
        raw = await redis.get(key)
        stored = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if not stored or stored != code_value:
            raise BusinessError("验证码无效或已过期")
        await redis.delete(key)

    async def register_portal(self, payload: RegisterRequest) -> RegisterResponse:
        """执行门户注册（ACCOUNT/EMAIL/PHONE 通道）：创建账户、资料、默认角色/部门。"""
        policy = get_register_policy(AccountType.PORTAL)
        if not policy.enabled:
            raise BusinessError("Portal registration is disabled")
        channel = (payload.register_channel or "ACCOUNT").strip().upper()
        email: str | None = None
        phone: str | None = None
        account_name: str | None = None
        if channel == "ACCOUNT":
            if not config_reader.get_bool("AUTH_REGISTER_PORTAL_ALLOW_ACCOUNT", True):
                raise BusinessError("用户名注册已关闭")
            account_name = require_account_login((payload.account or "").strip())
            if await self.account_repo.get_account_by_identifier(
                account_name, [AccountIdentityType.ACCOUNT]
            ) is not None:
                raise BusinessError("账号已存在")
            # 策略要求联系方式时，ACCOUNT 通道需在载荷中补齐（缺失则拒绝）。
            email = (payload.email or "").strip().lower() or None
            phone = (payload.phone or "").strip() or None
            if policy.require_email and not email:
                raise BusinessError("Email is required for registration")
            if policy.require_phone and not phone:
                raise BusinessError("Phone is required for registration")
        elif channel == "EMAIL":
            if not config_reader.get_bool("AUTH_REGISTER_PORTAL_ALLOW_EMAIL", True):
                raise BusinessError("邮箱注册已关闭")
            email = (payload.email or "").strip().lower() or None
            if not email or "@" not in email:
                raise BusinessError("邮箱格式不正确")
            await self.consume_register_code(channel="EMAIL", target=email, code=payload.otp_code)
            if await self.account_repo.get_account_by_identifier(
                email, [AccountIdentityType.EMAIL]
            ) is not None:
                raise BusinessError("邮箱已被使用")
            account_name = await self._allocate_account_from_contact(email.split("@", 1)[0])
        elif channel == "PHONE":
            if not config_reader.get_bool("AUTH_REGISTER_PORTAL_ALLOW_PHONE", False):
                raise BusinessError("手机注册已关闭")
            phone = (payload.phone or "").strip() or None
            if not phone:
                raise BusinessError("手机号不能为空")
            await self.consume_register_code(channel="PHONE", target=phone, code=payload.otp_code)
            if await self.account_repo.get_account_by_identifier(
                phone, [AccountIdentityType.PHONE]
            ) is not None:
                raise BusinessError("手机号已被使用")
            account_name = await self._allocate_account_from_contact(f"user{phone[-6:]}")
        else:
            raise BusinessError("不支持的注册通道")
        assert account_name
        nickname = f"user-{uuid4().hex[:8]}"
        async with transactional(self.db):
            account_payload = AccountCreateRequest(
                account=account_name,
                password=payload.password,
                account_type=AccountType.PORTAL,
                account_status=AccountStatusEnum.ENABLED,
                nickname=nickname,
                email=email,
                phone=phone,
                email_login_enabled=bool(email),
                phone_login_enabled=bool(phone),
                email_identity_verified=bool(email),
                phone_identity_verified=bool(phone),
            )
            account = await self.account_repo.create(
                account_payload,
                password_hash=await hash_password_async(payload.password),
            )
            await validate_and_record_password(
                self.db,
                account.id,
                payload.password,
                changed_by=account.id,
                change_reason="register",
                account=account,
                account_name=account_name,
                email=email,
                phone=phone,
            )
            await ProfileUserPortalRepository(self.db).upsert(
                ProfileUserPortalUpsertPayload(
                    account_id=account.id,
                    nickname=nickname,
                    phone=phone,
                    email=email,
                    avatar=None,
                    signature=None,
                    bio=None,
                    level=None,
                ),
            )
            await self._assign_register_defaults(account.id, AccountType.PORTAL)
        audit_snapshots.created_entity(account)
        audit_snapshots.subject(account_name)
        if email:
            try:
                await send_templated_mail(
                    "REGISTER_SUCCESS",
                    email,
                    {"app_name": settings.app.name, "account": account_name},
                )
            except BusinessError:
                pass
        response = RegisterResponse(
            account_id=account.id,
            account=account_name,
            account_type=AccountType.PORTAL,
        )
        await OperationAuditService(self.db).record(
            **_audit_record(
                module="auth",
                action="register",
                resource_type="auth",
                resource_id=account.id,
                success=True,
                account_id=account.id,
                account_type=AccountType.PORTAL.value,
                operator_name=account_name,
            )
        )
        return response

    async def _allocate_account_from_contact(self, base: str) -> str:
        """由邮箱/手机号派生唯一账号名（保留字母数字下划线，注入熵降低碰撞）。"""
        candidate = sanitize_account_base(base)
        if await self.account_repo.get_account_by_identifier(
            candidate, [AccountIdentityType.ACCOUNT]
        ) is None:
            return candidate
        # 极低概率碰撞：追加短熵后直接返回（一次查询收尾，避免逐序号循环）。
        return f"{candidate[:12]}{uuid4().hex[:6]}"

    async def _assign_register_defaults(self, account_id: str, account_type: AccountType) -> None:
        """为注册账户分配策略中配置的默认角色与部门。"""
        policy = get_register_policy(account_type)
        if policy.default_role_id:
            await self.account_repo.assign_account_to_role(
                AccountRoleAssignRequest(account_id=account_id, role_id=policy.default_role_id)
            )
        if policy.default_dept_id:
            await self.account_repo.assign_account_to_dept(
                AccountDeptAssignRequest(
                    account_id=account_id,
                    dept_id=policy.default_dept_id,
                    is_primary=True,
                )
            )
