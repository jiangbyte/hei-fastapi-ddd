""" Author: Charlie

兼容 re-export：领域模型已迁至 auth.domain.oauth.provider。
"""

from hei_fastapi_ddd.contexts.auth.domain.oauth.provider import (
    WECHAT_FAMILY,
    OauthProvider,
    OauthUserProfile,
)

__all__ = ["OauthProvider", "OauthUserProfile", "WECHAT_FAMILY"]
