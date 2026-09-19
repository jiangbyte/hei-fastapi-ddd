""" Author: Charlie

按 AccountType 读取登录/注册策略（sys_config UPPER_SNAKE）。
"""

from __future__ import annotations

from dataclasses import dataclass

from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.shared.config.enums import AccountType, account_config_key
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.types.business import AuthenticationError, BusinessError


@dataclass(frozen=True, slots=True)
class LoginTypePolicy:
    """登录类型策略：允许的登录渠道与失败锁定参数。"""

    allow_phone: bool
    phone_no_user_policy: str
    allow_email: bool
    email_no_user_policy: str
    allow_otp: bool
    failure_window_seconds: int
    max_failures: int
    lock_seconds: int


@dataclass(frozen=True, slots=True)
class RegisterTypePolicy:
    """注册类型策略：是否开启注册及必填项与默认归属。"""

    enabled: bool
    require_phone: bool
    require_email: bool
    default_role_id: str
    default_dept_id: str


@dataclass(frozen=True, slots=True)
class AuthOptions:
    """对外暴露的认证选项：登录/注册策略、三方登录入口与版权信息。"""

    account_type: AccountType
    allow_account: bool
    allow_email: bool
    allow_phone: bool
    allow_otp: bool
    register_enabled: bool
    register_require_phone: bool
    register_require_email: bool
    register_allow_account: bool
    register_allow_email: bool
    register_allow_phone: bool
    force_bind_email: bool
    force_bind_phone: bool
    password_change_verify_method: str
    copyright_text: str
    copyright_url: str
    oauth_providers: list[dict]


def get_login_policy(account_type: AccountType) -> LoginTypePolicy:
    """读取指定账户类型的登录策略（sys_config 覆盖 + 设置默认值）。"""
    prefix = "AUTH_LOGIN"
    shared_window = settings.auth.login_failure_window_seconds
    shared_max = settings.auth.login_account_max_failures
    shared_lock = settings.auth.login_lock_seconds
    return LoginTypePolicy(
        allow_phone=config_reader.get_bool(
            account_config_key(prefix, account_type, "ALLOW_PHONE"), True
        ),
        phone_no_user_policy=(
            config_reader.get(account_config_key(prefix, account_type, "PHONE_NO_USER_POLICY"))
            or "DENY"
        ).strip().upper(),
        allow_email=config_reader.get_bool(
            account_config_key(prefix, account_type, "ALLOW_EMAIL"), True
        ),
        email_no_user_policy=(
            config_reader.get(account_config_key(prefix, account_type, "EMAIL_NO_USER_POLICY"))
            or "DENY"
        ).strip().upper(),
        allow_otp=config_reader.get_bool(
            account_config_key(prefix, account_type, "ALLOW_OTP"), True
        ),
        failure_window_seconds=config_reader.get_int(
            account_config_key(prefix, account_type, "FAILURE_WINDOW_SECONDS"),
            shared_window,
        ),
        max_failures=config_reader.get_int(
            account_config_key(prefix, account_type, "MAX_FAILURES"),
            shared_max,
        ),
        lock_seconds=config_reader.get_int(
            account_config_key(prefix, account_type, "LOCK_SECONDS"),
            shared_lock,
        ),
    )


def get_register_policy(account_type: AccountType) -> RegisterTypePolicy:
    """读取指定账户类型的注册策略。"""
    prefix = "AUTH_REGISTER"
    default_enabled = (
        settings.auth.portal_register_enabled
        if account_type == AccountType.PORTAL
        else False
    )
    return RegisterTypePolicy(
        enabled=config_reader.get_bool(
            account_config_key(prefix, account_type, "ENABLED"),
            default_enabled,
        ),
        require_phone=config_reader.get_bool(
            account_config_key(prefix, account_type, "REQUIRE_PHONE"), False
        ),
        require_email=config_reader.get_bool(
            account_config_key(prefix, account_type, "REQUIRE_EMAIL"),
            account_type == AccountType.PORTAL,
        ),
        default_role_id=(
            config_reader.get(account_config_key(prefix, account_type, "DEFAULT_ROLE_ID")) or ""
        ).strip(),
        default_dept_id=(
            config_reader.get(account_config_key(prefix, account_type, "DEFAULT_DEPT_ID")) or ""
        ).strip(),
    )


def get_auth_options(account_type: AccountType) -> AuthOptions:
    """汇总登录与注册策略为对外认证选项。"""
    login = get_login_policy(account_type)
    register = get_register_policy(account_type)
    type_name = account_type.value
    return AuthOptions(
        account_type=account_type,
        allow_account=True,
        allow_email=login.allow_email,
        allow_phone=login.allow_phone,
        allow_otp=login.allow_otp,
        register_enabled=register.enabled,
        register_require_phone=register.require_phone,
        register_require_email=register.require_email,
        # ADMIN 端与 hei-boot 一致：注册通道选项硬编码关闭（不读配置）；
        # 仅 PORTAL 端读取 AUTH_REGISTER_PORTAL_ALLOW_* 配置。
        register_allow_account=(
            config_reader.get_bool(
                f"AUTH_REGISTER_{type_name}_ALLOW_ACCOUNT", True
            )
            if account_type == AccountType.PORTAL
            else False
        ),
        register_allow_email=(
            config_reader.get_bool(
                f"AUTH_REGISTER_{type_name}_ALLOW_EMAIL", True
            )
            if account_type == AccountType.PORTAL
            else False
        ),
        register_allow_phone=(
            config_reader.get_bool(
                f"AUTH_REGISTER_{type_name}_ALLOW_PHONE", False
            )
            if account_type == AccountType.PORTAL
            else False
        ),
        force_bind_email=config_reader.get_bool(
            f"AUTH_FORCE_BIND_{type_name}_EMAIL", False
        ),
        force_bind_phone=config_reader.get_bool(
            f"AUTH_FORCE_BIND_{type_name}_PHONE", False
        ),
        password_change_verify_method=(
            config_reader.get("PASSWORD_CHANGE_VERIFY_METHOD") or "OLD_PASSWORD"
        ).strip().upper(),
        copyright_text=(config_reader.get("COPYRIGHT_TEXT") or "").strip(),
        copyright_url=(config_reader.get("COPYRIGHT_URL") or "").strip(),
        oauth_providers=_oauth_provider_options(account_type),
    )


def _oauth_provider_options(account_type: AccountType) -> list[dict]:
    """读取三方登录提供商开关，构造 auth-options 下发的入口列表。"""
    from hei_fastapi_ddd.contexts.auth.domain.oauth.provider import OauthProvider

    options: list[dict] = []
    for provider in OauthProvider:
        if account_type == AccountType.ADMIN and provider == OauthProvider.WECHAT_MP:
            continue
        options.append(
            {
                "provider": provider.value,
                "label": provider.label,
                "enabled": config_reader.get_bool(
                    f"AUTH_OAUTH_{account_type.value}_{provider.value}_ENABLED", False
                ),
                "web_oauth": provider.web_oauth,
            }
        )
    return options


def ensure_identity_allowed(
    account_type: AccountType,
    identity_type: AccountIdentityType,
    *,
    login_mode: str = "PASSWORD",
) -> LoginTypePolicy:
    """校验登录渠道与身份类型是否被允许，违规抛业务错误。"""
    policy = get_login_policy(account_type)
    mode = (login_mode or "PASSWORD").strip().upper()
    if mode == "OTP" and not policy.allow_otp:
        raise BusinessError("OTP login is disabled")
    if identity_type == AccountIdentityType.EMAIL and not policy.allow_email:
        raise BusinessError("Email login is disabled")
    if identity_type == AccountIdentityType.PHONE and not policy.allow_phone:
        raise BusinessError("Phone login is disabled")
    if identity_type == AccountIdentityType.ACCOUNT and mode == "OTP":
        raise BusinessError("OTP login requires email or phone")
    return policy


def no_user_policy_for(
    policy: LoginTypePolicy,
    identity_type: AccountIdentityType,
) -> str:
    """返回指定身份类型对应的「无用户」处理策略。"""
    if identity_type == AccountIdentityType.EMAIL:
        return policy.email_no_user_policy
    if identity_type == AccountIdentityType.PHONE:
        return policy.phone_no_user_policy
    return "DENY"


def deny_if_locked_message() -> AuthenticationError:
    """构造账户锁定的认证错误。"""
    return AuthenticationError("Account is temporarily locked")
