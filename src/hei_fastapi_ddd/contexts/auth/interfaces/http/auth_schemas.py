""" Author: Charlie

认证请求/响应模型：登录、注册、忘记/重置密码、注销与账号注销等 Pydantic 模型。
"""

from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, model_validator

from hei_fastapi_ddd.contexts.auth.interfaces.http.oauth_schemas import OauthProviderOptionSchema
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt
from hei_fastapi_ddd.shared.security.account_login import require_account_login
from hei_fastapi_ddd.shared.security.transport import CaptchaMixin, PasswordKeyMixin
from hei_fastapi_ddd.shared.web.schema import ApiResponse


def _empty_as_none(value: object) -> object:
    """把空字符串规范为 None，供可选文本字段复用。"""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


# 空字符串视为 None 的可选字符串类型别名。
OptionalStr = Annotated[str | None, BeforeValidator(_empty_as_none)]


class CaptchaFormatQuery(ApiSchema):
    """验证码图片格式查询参数（svg 或 png）。"""

    image_format: str = Field(default="svg", alias="format", pattern="^(svg|png)$")


class LoginRequest(CaptchaMixin):
    """登录请求：账号 + 密码（或 OTP），密码经传输层加密后携带。"""

    account: str = Field(min_length=3, max_length=128)
    password: OptionalStr = Field(default=None, min_length=1, max_length=512)
    password_key_id: OptionalStr = Field(default=None, max_length=64)
    identity_type: AccountIdentityType = AccountIdentityType.ACCOUNT
    login_mode: Literal["PASSWORD", "OTP"] = "PASSWORD"
    otp_code: OptionalStr = Field(default=None, min_length=4, max_length=16)
    remember_me: WireBool = True
    account_type: AccountType = AccountType.ADMIN


class LoginPayload(ApiSchema):
    """登录服务载荷，包含目标账户类型。"""

    account: str
    password: str | None = None
    account_type: AccountType
    identity_type: AccountIdentityType = AccountIdentityType.ACCOUNT
    login_mode: str = "PASSWORD"
    otp_code: str | None = None
    remember_me: WireBool = True
    client_ip: str | None = None
    user_agent: str | None = None
    device_label: str | None = None


class LoginResponse(ApiSchema):
    """登录成功响应：会话 token 与账户信息。"""

    token: str | None = None
    account_id: str | None = None
    account_type: AccountType | None = None
    password_expired: WireBool = False
    password_expiry_warning_days: WireInt | None = None
    expires_in: WireInt | None = None
    force_bind_email: WireBool = False
    force_bind_phone: WireBool = False


class SendLoginCodeRequest(CaptchaMixin):
    """发送登录验证码请求：目标渠道与联系方式。"""

    target: str = Field(min_length=3, max_length=128)
    channel: Literal["EMAIL", "PHONE"]


class SiteFooterResponse(ApiSchema):
    """站点页脚公开信息（对齐 SiteFooterResult）。"""

    copyright_text: str = ""
    copyright_url: str = ""
    icp_number: str = ""
    icp_url: str = ""
    psb_number: str = ""
    psb_url: str = ""


class AuthOptionsResponse(ApiSchema):
    """登录/注册策略选项响应。"""

    account_type: AccountType
    allow_account: WireBool = True
    allow_email: WireBool = True
    allow_phone: WireBool = True
    allow_otp: WireBool = True
    register_enabled: WireBool = False
    register_require_phone: WireBool = False
    register_require_email: WireBool = False
    register_allow_account: WireBool = True
    register_allow_email: WireBool = True
    register_allow_phone: WireBool = False
    force_bind_email: WireBool = False
    force_bind_phone: WireBool = False
    password_change_verify_method: str = "OLD_PASSWORD"
    copyright_text: str = ""
    copyright_url: str = ""
    site_footer: SiteFooterResponse = Field(default_factory=SiteFooterResponse)
    oauth_providers: list[OauthProviderOptionSchema] = Field(default_factory=list)


class RegisterRequest(CaptchaMixin, PasswordKeyMixin):
    """门户注册请求：ACCOUNT / EMAIL / PHONE 通道，邮箱/手机通道需 OTP。"""

    register_channel: Literal["ACCOUNT", "EMAIL", "PHONE"]
    account: str | None = Field(default=None, min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=512)
    email: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=32)
    otp_code: OptionalStr = Field(default=None, min_length=4, max_length=16)

    @model_validator(mode="after")
    def validate_account_channel(self) -> "RegisterRequest":
        if self.register_channel == "ACCOUNT":
            self.account = require_account_login(self.account or "")
        return self


class SendRegisterCodeRequest(ApiSchema):
    """发送门户注册通道验证码请求。"""

    target: str = Field(min_length=3, max_length=128)
    channel: Literal["EMAIL", "PHONE"]
    captcha_id: str = Field(min_length=1, max_length=64)
    captcha_value: str = Field(min_length=1, max_length=64)


class ForgotPasswordByPhoneRequest(CaptchaMixin):
    """通过手机找回密码：校验图形验证码后向绑定手机发送重置 OTP。"""

    phone: str = Field(min_length=3, max_length=32)


class ResetPasswordByPhoneRequest(CaptchaMixin, PasswordKeyMixin):
    """通过手机 OTP 重置密码。"""

    phone: str = Field(min_length=3, max_length=32)
    otp_code: str = Field(min_length=4, max_length=16)
    password: str = Field(min_length=1, max_length=512)


class ForgotPasswordRequest(CaptchaMixin):
    """忘记密码请求：通过邮箱触发重置。"""

    email: str = Field(min_length=3, max_length=128)


class ResetPasswordRequest(CaptchaMixin, PasswordKeyMixin):
    """重置密码请求：携带重置 token 与新密码。"""

    email: OptionalStr = Field(default=None, min_length=3, max_length=128)
    token: str = Field(min_length=16, max_length=256)
    password: str = Field(min_length=1, max_length=512)


class RegisterResponse(ApiSchema):
    """注册成功响应。"""

    account_id: str
    account: str
    account_type: AccountType


class LogoutResponse(ApiSchema):
    """注销响应。"""

    success: WireBool = True


class CancelAccountRequest(ApiSchema):
    """账号注销请求。"""

    cancel_reason: str | None = Field(default=None, max_length=500)


class CancelAccountResponse(ApiSchema):
    """账号注销响应。"""

    success: WireBool = True


LoginApiResponse = ApiResponse[LoginResponse]
RegisterApiResponse = ApiResponse[RegisterResponse]
LogoutApiResponse = ApiResponse[LogoutResponse]
CancelAccountApiResponse = ApiResponse[CancelAccountResponse]
AuthOptionsApiResponse = ApiResponse[AuthOptionsResponse]
