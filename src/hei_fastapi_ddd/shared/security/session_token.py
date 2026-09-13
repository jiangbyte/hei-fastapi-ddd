""" Author: Charlie

从 HttpOnly Cookie（优先）或原始请求头（原生客户端）提取会话 token。

各端共用 Cookie 名；登录/登出时用「当前请求路径的父级」作为 Cookie Path
（例如 /api/vN/{client}/login -> /api/vN/{client}），由浏览器按 Path 隔离会话，
避免同域不同端口互相覆盖。不硬编码版本号或客户端段。
"""
from __future__ import annotations

from pathlib import PurePosixPath

from fastapi import Response
from starlette.requests import Request

from hei_fastapi_ddd.shared.config.settings import settings


def session_cookie_path_from_request(request: Request) -> str:
    """从认证相关请求路径推导 Cookie Path：.../login|logout -> 上一级目录。"""
    path = (getattr(getattr(request, "url", None), "path", None) or "").rstrip("/")
    if not path:
        return settings.auth.session_cookie_path
    parent = str(PurePosixPath(path).parent)
    if parent in {".", "/"}:
        return path
    return parent


def _raw_header_token(request: Request) -> str | None:
    """从配置请求头读取不透明会话 token；拒绝 HTTP Bearer 方案。"""
    header_name = (settings.auth.token_name or "Authorization").strip() or "Authorization"
    raw = request.headers.get(header_name)
    if not raw or not raw.strip():
        return None
    token = raw.strip()
    # 旧版/浏览器 ``Authorization: Bearer <jwt>`` 不用于 HEI 会话。
    if token.lower().startswith("bearer "):
        return None
    return token


def extract_session_token(request: Request, authorization: str | None = None) -> str | None:
    """优先会话 Cookie；否则回退到原始 Authorization（或 token_name）头。

    Cookie 端隔离由浏览器按 Path 完成；此处不解析路由。
    ``authorization`` 参数为调用方兼容保留；Bearer 方案会被忽略。建议仅传 ``request``。
    """
    if settings.auth.session_cookie_enabled:
        cookie = request.cookies.get(settings.auth.session_cookie_name)
        if cookie and cookie.strip():
            return cookie.strip()

    if authorization and authorization.strip():
        token = authorization.strip()
        if not token.lower().startswith("bearer "):
            return token

    return _raw_header_token(request)


def set_session_cookie(
    response: Response,
    token: str,
    *,
    request: Request,
    remember_me: bool = True,
) -> None:
    if not settings.auth.session_cookie_enabled:
        return
    max_age = (
        settings.auth.token_ttl_seconds if remember_me else settings.auth.token_ttl_short_seconds
    )
    same_site = settings.auth.session_cookie_samesite.lower()
    if same_site not in {"lax", "strict", "none"}:
        same_site = "lax"
    cookie_path = session_cookie_path_from_request(request)
    response.set_cookie(
        key=settings.auth.session_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.auth.session_cookie_secure or same_site == "none",
        samesite=same_site,  # type: ignore[arg-type]
        path=cookie_path,
    )
    # 清除旧版 Path=/ 共享 Cookie，避免继续被所有端带上。
    legacy_path = settings.auth.session_cookie_path
    if legacy_path != cookie_path:
        response.delete_cookie(
            key=settings.auth.session_cookie_name,
            path=legacy_path,
        )
    from hei_fastapi_ddd.shared.security.csrf import issue_csrf_cookie

    issue_csrf_cookie(response, max_age=max_age)


def clear_session_cookie(
    response: Response,
    *,
    request: Request,
) -> None:
    if not settings.auth.session_cookie_enabled:
        return
    cookie_path = session_cookie_path_from_request(request)
    response.delete_cookie(
        key=settings.auth.session_cookie_name,
        path=cookie_path,
    )
    # 兼容清理旧版 Path=/ Cookie
    response.delete_cookie(
        key=settings.auth.session_cookie_name,
        path=settings.auth.session_cookie_path,
    )
    from hei_fastapi_ddd.shared.security.csrf import clear_csrf_cookie

    clear_csrf_cookie(response)
