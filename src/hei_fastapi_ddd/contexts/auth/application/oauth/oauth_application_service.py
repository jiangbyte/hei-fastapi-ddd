""" Author: Charlie

三方登录服务：授权、回调、兑换、绑定/解绑、小程序登录与门户自动开户。

对齐 hei-boot AuthOauthServiceImpl 的流程与契约：
- state 一次性存储（Redis），回调后用 oauth_code 兑换登录结果，token 不进 URL。
- 管理端禁止三方自动开户（先密码登录再绑定）；门户可自动开户。
"""
import base64
import secrets
from typing import Any
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.schema.datetime import normalize_orm_datetimes
from hei_fastapi_ddd.shared.security.password import hash_password_async
from hei_fastapi_ddd.contexts.auth.infrastructure.oauth.client import OauthClientFacade
from hei_fastapi_ddd.contexts.auth.infrastructure.oauth.provider import WECHAT_FAMILY, OauthProvider, OauthUserProfile
from hei_fastapi_ddd.contexts.auth.infrastructure.persistence.oauth_repository import AccountOauthBindingRepository
from hei_fastapi_ddd.contexts.auth.interfaces.http.oauth_schemas import (
    OauthBindingResult,
    OauthProviderOptionSchema,
)
from hei_fastapi_ddd.contexts.auth.infrastructure.oauth.stores import (
    OauthExchangeStore,
    OauthStatePayload,
    OauthStateStore,
)
from hei_fastapi_ddd.contexts.auth.application.auth_application_service import AuthService
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.iam.application.account.password_helper import validate_and_record_password
from hei_fastapi_ddd.contexts.iam.application.api.account_api_adapter import AccountApiAdapter as AccountRepository
from hei_fastapi_ddd.contexts.iam.interfaces.http.account_schemas import (
    AccountCreateRequest,
    AccountDeptAssignRequest,
    AccountRoleAssignRequest,
)
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_repository import ProfileUserPortalRepository
from hei_fastapi_ddd.contexts.profile.interfaces.http.portal_schemas import ProfileUserPortalUpsertPayload


def _mask_open_id(open_id: str | None) -> str:
    """openid 脱敏：前 4 后 4，中间 ****。"""
    if not open_id:
        return ""
    value = open_id.strip()
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


class AuthOauthService:
    """三方登录应用服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = OauthClientFacade()
        self.state_store = OauthStateStore()
        self.exchange_store = OauthExchangeStore()
        self.binding_repo = AccountOauthBindingRepository(db)
        self.account_repo = AccountRepository(db)
        self.auth_service = AuthService(db)

    async def authorize(
        self,
        account_type: AccountType,
        provider_raw: str,
        intent: str | None,
        redirect: str | None,
        session_payload: Any | None = None,
    ) -> dict[str, str]:
        """发起 OAuth 授权，返回 {authorize_url, state}。"""
        provider = self._provider(provider_raw)
        if not provider.web_oauth:
            raise BusinessError("请使用小程序登录接口")
        await self.client.ensure_enabled(account_type, provider)
        normalized_intent = (intent or "LOGIN").strip().upper()
        if normalized_intent not in {"LOGIN", "BIND"}:
            raise BusinessError("不支持的 OAuth intent")
        payload = OauthStatePayload(
            account_type=account_type.value,
            intent=normalized_intent,
            provider=provider.value,
            redirect=redirect or None,
        )
        if normalized_intent == "BIND":
            if session_payload is None:
                raise BusinessError("绑定三方账号需要先登录")
            if session_payload.account_type != account_type:
                raise BusinessError("账号类型不匹配")
            payload.account_id = session_payload.account_id
        state = await self.state_store.save(payload)
        authorize_url = self.client.build_authorize_url(account_type, provider, state)
        return {"authorize_url": authorize_url, "state": state}

    async def handle_callback(
        self,
        account_type: AccountType,
        provider_raw: str,
        code: str | None,
        state: str | None,
    ) -> str:
        """处理网页回调，返回前端跳转 URL（带 oauth_code，不含 token）。"""
        provider = self._provider(provider_raw)
        frontend = self._frontend_callback(account_type)
        payload = await self.state_store.consume(state)
        if payload is None:
            return self._fail_redirect(frontend, "授权已过期，请重试")
        if (
            payload.account_type != account_type.value
            or payload.provider != provider.value
        ):
            return self._fail_redirect(frontend, "授权状态不匹配")
        try:
            profile = await self.client.login_by_code(
                account_type, provider, code, state
            )
            if payload.intent == "BIND":
                if not payload.account_id:
                    return self._fail_redirect(frontend, "绑定失败：未登录")
                async with transactional(self.db):
                    await self._bind_profile(payload.account_id, profile)
                return self._success_redirect(
                    frontend, oauth_code=None, redirect=payload.redirect, action="bound"
                )
            login = await self._login_or_create(account_type, profile)
            oauth_code = await self.exchange_store.save(login)
            return self._success_redirect(
                frontend, oauth_code=oauth_code, redirect=payload.redirect, action="login"
            )
        except BusinessError as exc:
            return self._fail_redirect(frontend, str(exc))
        except Exception:
            return self._fail_redirect(frontend, "三方登录失败")

    async def exchange(self, code: str | None) -> dict[str, Any]:
        """用一次性 oauth_code 兑换登录结果。"""
        return await self.exchange_store.consume(code)

    async def login_wechat_mp(self, account_type: AccountType, code: str | None) -> dict[str, Any]:
        """微信小程序 code2session 登录并签发会话。"""
        profile = await self.client.login_wechat_mp(account_type, code)
        label = profile.nickname or _mask_open_id(profile.open_id)
        audit_snapshots.subject(label)
        audit_snapshots.after(
            {
                "提供商": "微信小程序",
                "OpenID": _mask_open_id(profile.open_id),
            }
        )
        return await self._login_or_create(account_type, profile)

    async def list_current_bindings(self, account_id: str) -> list[OauthBindingResult]:
        """列出当前账号三方绑定。"""
        bindings = await self.binding_repo.list_by_account(account_id)
        results: list[OauthBindingResult] = []
        for binding in bindings:
            try:
                provider = self._provider(binding.provider)
                label = provider.label
            except ValueError:
                label = binding.provider
            normalize_orm_datetimes(binding)
            results.append(
                OauthBindingResult(
                    provider=binding.provider,
                    label=label,
                    open_id_masked=_mask_open_id(binding.open_id),
                    nickname=binding.nickname,
                    avatar=binding.avatar,
                    bound_at=binding.bound_at,
                )
            )
        return results

    async def bind_authorize(
        self,
        account_type: AccountType,
        provider_raw: str,
        session_payload: Any,
    ) -> dict[str, str]:
        """发起绑定授权。"""
        provider = self._provider(provider_raw)
        account_label = await self._account_identifier(
            session_payload.account_id, AccountIdentityType.ACCOUNT
        ) or session_payload.account_id
        audit_snapshots.subject(account_label)
        audit_snapshots.after({"提供商": provider.label})
        return await self.authorize(
            account_type, provider_raw, "BIND", None, session_payload
        )

    async def unbind(self, account_id: str, provider_raw: str) -> None:
        """解绑当前账号指定提供商。"""
        provider = self._provider(provider_raw)
        await self._assert_can_unbind(account_id, provider.value)
        binding = next(
            (
                item
                for item in await self.binding_repo.list_by_account(account_id)
                if item.provider == provider.value
            ),
            None,
        )
        if binding is not None:
            audit_snapshots.deleted_entity(binding)
        audit_snapshots.subject(account_id)
        async with transactional(self.db):
            await self.binding_repo.unbind(account_id, provider.value)

    async def admin_unbind(self, account_id: str, provider_raw: str) -> None:
        """管理端强制解绑指定账号的提供商。"""
        if not account_id or not account_id.strip():
            raise BusinessError("账号 ID 不能为空")
        provider = self._provider(provider_raw)
        await self._assert_can_unbind(account_id, provider.value)
        binding = next(
            (
                item
                for item in await self.binding_repo.list_by_account(account_id)
                if item.provider == provider.value
            ),
            None,
        )
        if binding is not None:
            audit_snapshots.deleted_entity(binding)
        audit_snapshots.subject(account_id)
        async with transactional(self.db):
            await self.binding_repo.unbind(account_id, provider.value)

    def list_provider_options(self, account_type: AccountType) -> list[OauthProviderOptionSchema]:
        """列出 auth-options 下发的三方登录入口（管理端隐藏小程序）。"""
        options: list[OauthProviderOptionSchema] = []
        for provider in OauthProvider:
            if account_type == AccountType.ADMIN and provider == OauthProvider.WECHAT_MP:
                continue
            enabled = config_reader.get_bool(
                f"AUTH_OAUTH_{account_type.value}_{provider.value}_ENABLED", False
            )
            options.append(
                OauthProviderOptionSchema(
                    provider=provider.value,
                    label=provider.label,
                    enabled=enabled,
                    web_oauth=provider.web_oauth,
                )
            )
        return options

    # ------------------------------------------------------------------ 内部

    async def _login_or_create(
        self, account_type: AccountType, profile: OauthUserProfile
    ) -> dict[str, Any]:
        """按绑定关系登录，门户未绑定时自动开户。"""
        binding = await self._resolve_binding(profile)
        if binding is not None:
            account = await self.account_repo.get_by_id(binding.account_id)
            if account is None:
                raise BusinessError("绑定账号不存在")
            if str(account.account_type) != account_type.value:
                raise BusinessError("账号类型不匹配")
            await self.binding_repo.upsert_binding(
                account.id,
                profile.provider,
                profile.open_id,
                profile.union_id,
                profile.nickname,
                profile.avatar,
                profile.raw_profile_json,
            )
            label = profile.nickname or await self._account_identifier(
                account.id, AccountIdentityType.ACCOUNT
            )
            return await self._issue(account, account_type, label)

        if account_type == AccountType.ADMIN:
            raise BusinessError("请先使用账号密码登录后再绑定该三方账号")

        # 门户自动建号
        async with transactional(self.db):
            account_name = await self._allocate_oauth_account_name(profile)
            raw_password = "oauth:" + base64.urlsafe_b64encode(
                secrets.token_bytes(32)
            ).decode().rstrip("=")
            nickname = profile.nickname or f"user-{account_name[-8:]}"
            account = await self.account_repo.create(
                AccountCreateRequest(
                    account=account_name,
                    password=raw_password,
                    account_type=AccountType.PORTAL,
                    account_status=AccountStatusEnum.ENABLED,
                    nickname=nickname,
                ),
                password_hash=await hash_password_async(raw_password),
            )
            await validate_and_record_password(
                self.db,
                account.id,
                raw_password,
                changed_by=account.id,
                change_reason="oauth_register",
                account=account,
                account_name=account_name,
            )
            await ProfileUserPortalRepository(self.db).upsert(
                ProfileUserPortalUpsertPayload(
                    account_id=account.id,
                    nickname=nickname,
                    avatar=profile.avatar,
                )
            )
            await self._assign_register_defaults(account.id)
            await self.binding_repo.upsert_binding(
                account.id,
                profile.provider,
                profile.open_id,
                profile.union_id,
                profile.nickname,
                profile.avatar,
                profile.raw_profile_json,
            )
        return await self._issue(account, AccountType.PORTAL, account_name)

    async def _bind_profile(self, account_id: str, profile: OauthUserProfile) -> None:
        """将三方资料绑定到指定账号，校验冲突。"""
        existing = await self._resolve_binding(profile)
        if existing is not None and existing.account_id != account_id:
            raise BusinessError("该三方账号已绑定其他用户")
        same_provider = [
            item
            for item in await self.binding_repo.list_by_account(account_id)
            if item.provider == profile.provider
        ]
        if same_provider and same_provider[0].open_id != profile.open_id:
            raise BusinessError(f"已绑定其他 {profile.provider} 账号，请先解绑")
        await self.binding_repo.upsert_binding(
            account_id,
            profile.provider,
            profile.open_id,
            profile.union_id,
            profile.nickname,
            profile.avatar,
            profile.raw_profile_json,
        )

    async def _resolve_binding(self, profile: OauthUserProfile):
        """按 unionid（微信族）或 provider+openid 解析绑定。"""
        if profile.provider in WECHAT_FAMILY and profile.union_id:
            by_union = await self.binding_repo.find_by_wechat_union_id(profile.union_id)
            if by_union is not None:
                return by_union
        return await self.binding_repo.find_by_provider_open_id(
            profile.provider, profile.open_id
        )

    async def _assert_can_unbind(self, account_id: str, provider: str) -> None:
        """解绑前确保至少保留一种登录方式。"""
        bindings = await self.binding_repo.list_by_account(account_id)
        target = next(
            (item for item in bindings if item.provider == provider), None
        )
        if target is None:
            return
        has_account = await self.account_repo.has_identity(
            account_id, AccountIdentityType.ACCOUNT
        )
        has_email = await self.account_repo.has_identity(
            account_id, AccountIdentityType.EMAIL
        )
        has_phone = await self.account_repo.has_identity(
            account_id, AccountIdentityType.PHONE
        )
        other_login_ways = (
            (1 if has_account else 0)
            + (1 if has_email else 0)
            + (1 if has_phone else 0)
            + max(0, len(bindings) - 1)
        )
        if other_login_ways <= 0:
            raise BusinessError("无法解绑：请至少保留一种登录方式")

    async def _allocate_oauth_account_name(self, profile: OauthUserProfile) -> str:
        """按提供商前缀 + openid 片段生成唯一账号名。"""
        prefix = {
            OauthProvider.GITHUB.value: "gh_",
            OauthProvider.GITEE.value: "ge_",
            OauthProvider.QQ.value: "qq_",
            OauthProvider.WECHAT_OPEN.value: "wx_",
            OauthProvider.WECHAT_MP.value: "wx_",
        }[profile.provider]
        suffix = "".join(ch for ch in profile.open_id if ch.isalnum())
        if len(suffix) > 12:
            suffix = suffix[:12]
        if not suffix:
            suffix = str(secrets.randbelow(1_000_000))
        base = (prefix + suffix).lower()
        candidate = base
        index = 0
        while await self.account_repo.get_account_by_identifier(
            candidate, [AccountIdentityType.ACCOUNT]
        ) is not None:
            index += 1
            candidate = f"{base}{index}"
        return candidate

    async def _account_identifier(
        self, account_id: str, identity_type: AccountIdentityType
    ) -> str:
        """返回账号主标识。"""
        identities = await self.account_repo.list_identities_by_account_ids([account_id])
        for item in identities:
            if item.identity_type == identity_type.value and item.is_primary:
                return item.identifier or ""
        for item in identities:
            if item.identity_type == identity_type.value:
                return item.identifier or ""
        return ""

    async def _assign_register_defaults(self, account_id: str) -> None:
        """为自动开户账户分配策略配置的默认角色与部门。"""
        from hei_fastapi_ddd.contexts.auth.domain.policy import get_register_policy

        policy = get_register_policy(AccountType.PORTAL)
        if policy.default_role_id:
            await self.account_repo.assign_account_to_role(
                AccountRoleAssignRequest(
                    account_id=account_id, role_id=policy.default_role_id
                )
            )
        if policy.default_dept_id:
            await self.account_repo.assign_account_to_dept(
                AccountDeptAssignRequest(
                    account_id=account_id,
                    dept_id=policy.default_dept_id,
                    is_primary=True,
                )
            )

    async def _issue(
        self,
        account: SysAccount,
        account_type: AccountType,
        login_label: str | None,
    ) -> dict[str, Any]:
        """签发会话并返回登录结果字典。"""
        result = await self.auth_service.issue_oauth_session(
            account,
            account_type,
            login_label=login_label,
        )
        return result.model_dump()

    def _provider(self, raw: str) -> OauthProvider:
        try:
            return OauthProvider.from_raw(raw)
        except ValueError as exc:
            raise BusinessError(f"Unsupported provider: {raw}") from exc

    def _frontend_callback(self, account_type: AccountType) -> str:
        """返回 OAuth 前端回调页地址（配置优先，默认 /auth/oauth/callback）。"""
        key = (
            "AUTH_OAUTH_FRONTEND_CALLBACK_ADMIN"
            if account_type == AccountType.ADMIN
            else "AUTH_OAUTH_FRONTEND_CALLBACK_PORTAL"
        )
        configured = (config_reader.get(key) or "").strip()
        return configured or "/auth/oauth/callback"

    def _success_redirect(
        self,
        frontend: str,
        oauth_code: str | None,
        redirect: str | None,
        action: str,
    ) -> str:
        """构造成功跳转 URL（登录场景携带一次性 oauth_code，token 不进 URL）。"""
        params: dict[str, str] = {"oauth_status": "ok", "oauth_action": action}
        if oauth_code:
            params["oauth_code"] = oauth_code
        if redirect:
            params["redirect"] = redirect
        return f"{frontend}?{urlencode(params)}"

    def _fail_redirect(self, frontend: str, message: str) -> str:
        """构造失败跳转 URL。"""
        return f"{frontend}?{urlencode({'oauth_status': 'error', 'oauth_message': message})}"
