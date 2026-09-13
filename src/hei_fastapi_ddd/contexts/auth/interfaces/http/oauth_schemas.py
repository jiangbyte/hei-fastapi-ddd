""" Author: Charlie

OAuth 请求/响应模型：授权、兑换、绑定、小程序登录（对齐 hei-boot 契约）。
"""

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool


class OauthAuthorizeResult(ApiSchema):
    """发起 OAuth 授权的响应。"""

    authorize_url: str
    state: str


class OauthProviderOptionSchema(ApiSchema):
    """auth-options 中下发的三方登录入口。"""

    provider: str
    label: str
    enabled: WireBool = False
    web_oauth: WireBool = True


class OauthBindingResult(ApiSchema):
    """当前用户三方绑定列表项。"""

    provider: str
    label: str
    open_id_masked: str = ""
    nickname: str | None = None
    avatar: str | None = None
    bound_at: datetime | None = None


class OauthExchangeRequest(ApiSchema):
    """用一次性兑换码换取登录结果。"""

    code: str = Field(min_length=1, max_length=128)


class WechatMpLoginRequest(ApiSchema):
    """微信小程序登录请求。"""

    code: str = Field(min_length=1, max_length=512)


class AdminOauthUnbindRequest(ApiSchema):
    """管理端强制解绑三方账号。"""

    account_id: str = Field(min_length=1, max_length=64)
    provider: str = Field(min_length=1, max_length=32)
