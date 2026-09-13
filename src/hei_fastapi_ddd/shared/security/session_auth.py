""" Author: Charlie

HTTP 会话解析的单一入口（中间件 + Depends）。
"""
from __future__ import annotations

import asyncio

from starlette.requests import Request

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.exceptions.business import AuthenticationError
from hei_fastapi_ddd.shared.network.client_ip import get_client_ip
from hei_fastapi_ddd.shared.observability.context import account_id_ctx, account_type_ctx
from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store
from hei_fastapi_ddd.shared.security.session_token import extract_session_token

_STATE_SESSION = "hei_session"
_STATE_TOKEN = "hei_session_token"


def get_request_session(request: Request) -> SessionPayload | None:
    """返回本请求已解析的会话（若有）。"""
    return getattr(request.state, _STATE_SESSION, None)


def get_request_session_token(request: Request) -> str | None:
    """返回本请求已解析的 token（若有）。"""
    return getattr(request.state, _STATE_TOKEN, None)


def _validate_session_ip(request: Request, session: SessionPayload) -> None:
    """按配置校验会话 IP 绑定，防止 token 被盗用。"""
    if not settings.auth.session_bind_ip:
        return
    session_ip = session.client_ip
    if not session_ip:
        return
    current_ip = get_client_ip(request)
    if current_ip and current_ip != session_ip:
        raise AuthenticationError("Session IP mismatch — token may have been stolen")


def _validate_session_user_agent(request: Request, session: SessionPayload) -> None:
    """按配置校验会话 UA 绑定。"""
    if not settings.auth.session_bind_user_agent:
        return
    session_ua = session.user_agent
    if not session_ua:
        return
    current_ua = request.headers.get("user-agent")
    if current_ua and current_ua != session_ua:
        raise AuthenticationError("Session User-Agent mismatch")


def _touch_session_background(token: str) -> None:
    """在事件循环后台滑动会话 TTL（不阻塞请求响应）。"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(session_store.touch(token))
    except RuntimeError:
        pass


def _bind_context(session: SessionPayload) -> None:
    """把账户信息绑定到上下文与日志上下文。"""
    account_id_ctx.set(session.account_id)
    account_type_ctx.set(session.account_type)
    from hei_fastapi_ddd.shared.observability.context import bind_request_log_context

    bind_request_log_context(
        account_id=session.account_id,
        account_type=session.account_type,
    )


def _cache_on_request(request: Request, token: str, session: SessionPayload) -> None:
    """把会话与 token 缓存到请求状态，避免同请求重复解析。"""
    setattr(request.state, _STATE_SESSION, session)
    setattr(request.state, _STATE_TOKEN, token)


async def resolve_request_session(
    request: Request,
    *,
    required: bool = True,
    touch: bool = True,
    bind_context: bool = True,
) -> SessionPayload | None:
    """每请求加载并校验会话一次；复用 ``request.state`` 缓存。

    优先 Cookie；原生客户端可在 ``settings.auth.token_name``（默认 Authorization）
    头发送不透明 token。不支持 HTTP ``Bearer`` 方案，会被忽略。
    """
    cached = get_request_session(request)
    if cached is not None:
        if bind_context:
            _bind_context(cached)
        return cached

    token = extract_session_token(request)
    if not token:
        if required:
            raise AuthenticationError("Missing authorization token")
        return None

    session = await session_store.get(token)
    if session is None:
        if required:
            raise AuthenticationError("Invalid or expired token")
        return None

    _validate_session_ip(request, session)
    _validate_session_user_agent(request, session)
    _cache_on_request(request, token, session)

    if bind_context:
        _bind_context(session)
    if touch:
        _touch_session_background(token)
    return session
