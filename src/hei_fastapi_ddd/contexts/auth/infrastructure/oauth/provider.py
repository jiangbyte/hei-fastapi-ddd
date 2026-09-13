""" Author: Charlie

三方登录提供商与统一用户资料（对齐 hei-boot OauthProvider / OauthUserProfile）。
"""
from dataclasses import dataclass
from enum import StrEnum


class OauthProvider(StrEnum):
    """支持的三方登录提供商。"""

    GITHUB = "GITHUB"
    GITEE = "GITEE"
    QQ = "QQ"
    WECHAT_OPEN = "WECHAT_OPEN"
    WECHAT_MP = "WECHAT_MP"

    @property
    def label(self) -> str:
        """提供商展示名。"""
        return {
            OauthProvider.GITHUB: "GitHub",
            OauthProvider.GITEE: "Gitee",
            OauthProvider.QQ: "QQ",
            OauthProvider.WECHAT_OPEN: "微信",
            OauthProvider.WECHAT_MP: "微信小程序",
        }[self]

    @property
    def web_oauth(self) -> bool:
        """是否走网页 OAuth 授权码流程（小程序为 False）。"""
        return self != OauthProvider.WECHAT_MP

    @staticmethod
    def from_raw(raw: str) -> "OauthProvider":
        """按名称解析提供商，非法值抛 ValueError。"""
        if not raw or not raw.strip():
            raise ValueError("provider required")
        return OauthProvider(raw.strip().upper())


WECHAT_FAMILY = {OauthProvider.WECHAT_OPEN, OauthProvider.WECHAT_MP}


@dataclass(slots=True)
class OauthUserProfile:
    """统一的三方用户资料。"""

    provider: str
    open_id: str
    union_id: str | None = None
    nickname: str | None = None
    avatar: str | None = None
    raw_profile_json: str = "{}"
