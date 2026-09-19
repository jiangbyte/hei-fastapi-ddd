""" Author: Charlie

OAuth 客户端门面：构建授权 URL、用授权码换取用户资料，以及微信小程序登录。

参考 hei-boot OauthClientFacade（JustAuth）；GitHub/Gitee token 交换使用 Authlib，其余平台保留 httpx。
凭据统一从 sys_config（AUTH_OAUTH_{TYPE}_{PROVIDER}_*）读取。
"""
import json
import re
from typing import Any
from urllib.parse import urlencode

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client

from hei_fastapi_ddd.contexts.auth.infrastructure.oauth.provider import (
    OauthProvider,
    OauthUserProfile,
)
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.http.client import get_http_client
from hei_fastapi_ddd.types.business import BusinessError


def oauth_config_key(account_type: AccountType, provider: OauthProvider, field: str) -> str:
    """构造 AUTH_OAUTH_{ACCOUNT_TYPE}_{PROVIDER}_{FIELD} 配置键。"""
    return f"AUTH_OAUTH_{account_type.value}_{provider.value}_{field}"


class OauthClientFacade:
    """OAuth 平台客户端工厂：授权/换码/取资料，配置驱动。"""

    # 各提供商官方端点。
    _AUTHORIZE = {
        OauthProvider.GITHUB: "https://github.com/login/oauth/authorize",
        OauthProvider.GITEE: "https://gitee.com/oauth/authorize",
        OauthProvider.QQ: "https://graph.qq.com/oauth2.0/authorize",
        OauthProvider.WECHAT_OPEN: "https://open.weixin.qq.com/connect/qrconnect",
    }
    _TOKEN = {
        OauthProvider.GITHUB: "https://github.com/login/oauth/access_token",
        OauthProvider.GITEE: "https://gitee.com/oauth/token",
        OauthProvider.QQ: "https://graph.qq.com/oauth2.0/token",
        OauthProvider.WECHAT_OPEN: "https://api.weixin.qq.com/sns/oauth2/access_token",
    }

    async def ensure_enabled(self, account_type: AccountType, provider: OauthProvider) -> None:
        """校验提供商在该账户类型下已启用，未启用抛业务错误。"""
        enabled = config_reader.get_bool(
            oauth_config_key(account_type, provider, "ENABLED"), False
        )
        if not enabled:
            raise BusinessError(f"{provider.label} 登录未启用")

    def _credentials(self, account_type: AccountType, provider: OauthProvider) -> tuple[str, str]:
        """返回 (client_id, client_secret)，兼容 CLIENT_ID/APP_ID 两种命名。"""
        client_id = (config_reader.get(oauth_config_key(account_type, provider, "CLIENT_ID")) or "").strip()
        client_id = client_id or (config_reader.get(oauth_config_key(account_type, provider, "APP_ID")) or "").strip()
        secret = (config_reader.get(oauth_config_key(account_type, provider, "CLIENT_SECRET")) or "").strip()
        secret = secret or (config_reader.get(oauth_config_key(account_type, provider, "APP_SECRET")) or "").strip()
        if not client_id or not secret:
            raise BusinessError(f"{provider.label} 未配置 ClientId/Secret")
        return client_id, secret

    def _redirect_uri(self, account_type: AccountType, provider: OauthProvider) -> str:
        """返回配置的回调地址，未配置时抛业务错误。"""
        uri = (config_reader.get(oauth_config_key(account_type, provider, "REDIRECT_URI")) or "").strip()
        if not uri:
            raise BusinessError(f"请配置 {oauth_config_key(account_type, provider, 'REDIRECT_URI')}")
        return uri

    def build_authorize_url(
        self, account_type: AccountType, provider: OauthProvider, state: str
    ) -> str:
        """构造授权 URL。"""
        if not provider.web_oauth:
            raise BusinessError("该提供商不支持网页授权")
        self.ensure_enabled(account_type, provider)
        client_id, _ = self._credentials(account_type, provider)
        redirect_uri = self._redirect_uri(account_type, provider)
        base = self._AUTHORIZE[provider]
        params: dict[str, str] = {}
        if provider == OauthProvider.WECHAT_OPEN:
            params = {
                "appid": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "snsapi_login",
                "state": state,
            }
            return f"{base}?{urlencode(params)}#wechat_redirect"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        if provider == OauthProvider.GITHUB:
            params["scope"] = "read:user"
        if provider == OauthProvider.GITEE:
            params["response_type"] = "code"
        if provider == OauthProvider.QQ:
            params["response_type"] = "code"
        return f"{base}?{urlencode(params)}"

    async def login_by_code(
        self,
        account_type: AccountType,
        provider: OauthProvider,
        code: str | None,
        state: str | None,
    ) -> OauthUserProfile:
        """用授权码换取三方用户资料。"""
        if not provider.web_oauth:
            raise BusinessError("该提供商不支持网页授权回调")
        if not code or not code.strip():
            raise BusinessError("缺少授权码 code")
        self.ensure_enabled(account_type, provider)
        client_id, client_secret = self._credentials(account_type, provider)
        redirect_uri = self._redirect_uri(account_type, provider)
        if provider == OauthProvider.GITHUB:
            return await self._login_github(client_id, client_secret, code, redirect_uri)
        if provider == OauthProvider.GITEE:
            return await self._login_gitee(client_id, client_secret, code, redirect_uri)
        if provider == OauthProvider.QQ:
            return await self._login_qq(client_id, client_secret, code, redirect_uri)
        if provider == OauthProvider.WECHAT_OPEN:
            return await self._login_wechat_open(client_id, client_secret, code)
        raise BusinessError(f"Unsupported provider: {provider}")

    async def login_wechat_mp(self, account_type: AccountType, code: str | None) -> OauthUserProfile:
        """微信小程序 code2session 登录。"""
        if account_type != AccountType.PORTAL:
            raise BusinessError("管理端暂不支持小程序登录")
        self.ensure_enabled(account_type, OauthProvider.WECHAT_MP)
        app_id, app_secret = self._credentials(account_type, OauthProvider.WECHAT_MP)
        if not code or not code.strip():
            raise BusinessError("缺少 code")
        url = (
            "https://api.weixin.qq.com/sns/jscode2session?"
            + urlencode(
                {
                    "appid": app_id,
                    "secret": app_secret,
                    "js_code": code.strip(),
                    "grant_type": "authorization_code",
                }
            )
        )
        data = await self._get_json(url)
        if data.get("errcode"):
            raise BusinessError(f"微信小程序登录失败: {data.get('errmsg') or data.get('errcode')}")
        open_id = str(data.get("openid") or "")
        if not open_id:
            raise BusinessError("微信小程序登录失败: 未返回 openid")
        return OauthUserProfile(
            provider=OauthProvider.WECHAT_MP.value,
            open_id=open_id,
            union_id=str(data["unionid"]) if data.get("unionid") else None,
            raw_profile_json=json.dumps(data, ensure_ascii=False),
        )

    async def _login_github(
        self, client_id: str, client_secret: str, code: str, redirect_uri: str
    ) -> OauthUserProfile:
        token_url = self._TOKEN[OauthProvider.GITHUB]
        client = AsyncOAuth2Client(client_id=client_id, client_secret=client_secret)
        try:
            token = await client.fetch_token(
                token_url,
                code=code,
                redirect_uri=redirect_uri,
                headers={"Accept": "application/json"},
            )
        except Exception as exc:
            raise BusinessError("GitHub 授权失败: token 交换错误") from exc
        access_token = str(token.get("access_token") or "")
        if not access_token:
            raise BusinessError("GitHub 授权失败: 未返回 access_token")
        user = await self._get_json(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        raw = json.dumps(user, ensure_ascii=False)
        return OauthUserProfile(
            provider=OauthProvider.GITHUB.value,
            open_id=str(user.get("id") or ""),
            nickname=str(user.get("name") or user.get("login") or ""),
            avatar=user.get("avatar_url"),
            raw_profile_json=raw,
        )

    async def _login_gitee(
        self, client_id: str, client_secret: str, code: str, redirect_uri: str
    ) -> OauthUserProfile:
        token_url = self._TOKEN[OauthProvider.GITEE]
        client = AsyncOAuth2Client(client_id=client_id, client_secret=client_secret)
        try:
            token = await client.fetch_token(
                token_url,
                code=code,
                redirect_uri=redirect_uri,
                grant_type="authorization_code",
            )
        except Exception as exc:
            raise BusinessError("Gitee 授权失败: token 交换错误") from exc
        access_token = str(token.get("access_token") or "")
        if not access_token:
            raise BusinessError("Gitee 授权失败: 未返回 access_token")
        user = await self._get_json(
            "https://gitee.com/api/v5/user?" + urlencode({"access_token": access_token})
        )
        raw = json.dumps(user, ensure_ascii=False)
        return OauthUserProfile(
            provider=OauthProvider.GITEE.value,
            open_id=str(user.get("id") or ""),
            nickname=str(user.get("name") or user.get("login") or ""),
            avatar=user.get("avatar_url"),
            raw_profile_json=raw,
        )

    async def _login_qq(
        self, client_id: str, client_secret: str, code: str, redirect_uri: str
    ) -> OauthUserProfile:
        # QQ 令牌接口返回表单格式文本（access_token=...&expires_in=...）。
        token_url = (
            self._TOKEN[OauthProvider.QQ]
            + "?"
            + urlencode(
                {
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                }
            )
        )
        token_text = await self._get_text(token_url)
        token_params = dict(
            item.split("=", 1) for item in token_text.split("&") if "=" in item
        )
        access_token = token_params.get("access_token", "")
        if not access_token:
            raise BusinessError("QQ 授权失败: 未返回 access_token")
        # openid 接口返回 callback( {...} ); 形式。
        me_text = await self._get_text(
            "https://graph.qq.com/oauth2.0/me?" + urlencode({"access_token": access_token})
        )
        match = re.search(r"\{.*?\}", me_text, re.DOTALL)
        open_id = ""
        if match:
            try:
                open_id = str(json.loads(match.group(0)).get("openid") or "")
            except ValueError:
                open_id = ""
        if not open_id:
            raise BusinessError("QQ 授权失败: 未返回 openid")
        user = await self._get_json(
            "https://graph.qq.com/user/get_user_info?"
            + urlencode(
                {
                    "access_token": access_token,
                    "oauth_consumer_key": client_id,
                    "openid": open_id,
                }
            )
        )
        raw = json.dumps({"openid": open_id, **user}, ensure_ascii=False)
        return OauthUserProfile(
            provider=OauthProvider.QQ.value,
            open_id=open_id,
            nickname=str(user.get("nickname") or ""),
            avatar=str(user.get("figureurl_qq_2") or user.get("figureurl_qq_1") or ""),
            raw_profile_json=raw,
        )

    async def _login_wechat_open(
        self, app_id: str, app_secret: str, code: str
    ) -> OauthUserProfile:
        data = await self._get_json(
            self._TOKEN[OauthProvider.WECHAT_OPEN]
            + "?"
            + urlencode(
                {
                    "appid": app_id,
                    "secret": app_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                }
            )
        )
        if data.get("errcode"):
            raise BusinessError(f"微信登录失败: {data.get('errmsg') or data.get('errcode')}")
        access_token = str(data.get("access_token") or "")
        open_id = str(data.get("openid") or "")
        if not access_token or not open_id:
            raise BusinessError("微信登录失败: 未返回 access_token/openid")
        union_id = str(data["unionid"]) if data.get("unionid") else None
        user = await self._get_json(
            "https://api.weixin.qq.com/sns/userinfo?"
            + urlencode({"access_token": access_token, "openid": open_id})
        )
        raw = json.dumps({**data, **user}, ensure_ascii=False)
        return OauthUserProfile(
            provider=OauthProvider.WECHAT_OPEN.value,
            open_id=open_id,
            union_id=union_id or (str(user["unionid"]) if user.get("unionid") else None),
            nickname=str(user.get("nickname") or ""),
            avatar=user.get("headimgurl"),
            raw_profile_json=raw,
        )

    async def _get_json(self, url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
        client = get_http_client()
        try:
            resp: httpx.Response = await client.get(url, headers=headers)
        except Exception as exc:
            raise BusinessError("三方登录失败: 网络请求错误") from exc
        if resp.status_code >= 400:
            raise BusinessError(f"三方登录失败: HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise BusinessError("三方登录失败: 响应解析错误") from exc
        if not isinstance(data, dict):
            raise BusinessError("三方登录失败: 响应格式错误")
        return data

    async def _get_text(self, url: str) -> str:
        client = get_http_client()
        try:
            resp: httpx.Response = await client.get(url)
        except Exception as exc:
            raise BusinessError("三方登录失败: 网络请求错误") from exc
        if resp.status_code >= 400:
            raise BusinessError(f"三方登录失败: HTTP {resp.status_code}")
        return resp.text

    async def _post_form_json(
        self,
        url: str,
        data: dict[str, str],
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        client = get_http_client()
        try:
            resp: httpx.Response = await client.post(url, data=data, headers=headers)
        except Exception as exc:
            raise BusinessError("三方登录失败: 网络请求错误") from exc
        if resp.status_code >= 400:
            raise BusinessError(f"三方登录失败: HTTP {resp.status_code}")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise BusinessError("三方登录失败: 响应解析错误") from exc
        if not isinstance(payload, dict):
            raise BusinessError("三方登录失败: 响应格式错误")
        return payload
