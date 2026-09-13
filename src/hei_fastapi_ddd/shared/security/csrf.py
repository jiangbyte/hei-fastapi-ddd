"""Author: Charlie

Cookie 双提交 CSRF：HEI_CSRF cookie + X-HEI-CSRF 头。
"""

from __future__ import annotations

import secrets

from fastapi import Response
from starlette.requests import Request

from hei_fastapi_ddd.shared.config.settings import settings

CSRF_COOKIE_NAME = "HEI_CSRF"
CSRF_HEADER_NAME = "X-HEI-CSRF"


def issue_csrf_cookie(response: Response, *, max_age: int | None = None) -> None:
    """登录成功后下发可读 CSRF Cookie（Path=/ 便于 SPA 读取）。"""
    if not settings.auth.session_cookie_enabled:
        return
    same_site = settings.auth.session_cookie_samesite.lower()
    if same_site not in {"lax", "strict", "none"}:
        same_site = "lax"
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=secrets.token_hex(32),
        max_age=max_age if max_age and max_age > 0 else None,
        httponly=False,
        secure=settings.auth.session_cookie_secure or same_site == "none",
        samesite=same_site,  # type: ignore[arg-type]
        path="/",
    )


def clear_csrf_cookie(response: Response) -> None:
    """登出时清除 CSRF Cookie。"""
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


def csrf_cookie_present(request: Request) -> str | None:
    return request.cookies.get(CSRF_COOKIE_NAME)


def session_cookie_present(request: Request) -> bool:
    if not settings.auth.session_cookie_enabled:
        return False
    name = settings.auth.session_cookie_name or "Authorization"
    return bool((request.cookies.get(name) or "").strip())


def validate_csrf(request: Request) -> str | None:
    """校验失败返回错误信息，成功返回 None。"""
    method = (request.method or "").upper()
    if method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return None
    path = (request.url.path or "").lower()
    if "/oauth/" in path and path.endswith("/callback"):
        return None
    if path.endswith("/health") or path.endswith("/ready"):
        return None
    if not session_cookie_present(request):
        return None
    cookie = csrf_cookie_present(request)
    if not cookie:
        return "CSRF token missing"
    header = request.headers.get(CSRF_HEADER_NAME) or ""
    if header != cookie:
        return "CSRF token mismatch"
    return None
