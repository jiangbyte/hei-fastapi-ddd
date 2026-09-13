""" Author: Charlie

会话 token 提取：cookie 优先，无 Bearer 方案；端隔离由 Cookie Path 完成。
"""
from unittest.mock import MagicMock

from starlette.requests import Request
from starlette.responses import Response

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.security.session_token import (
    extract_session_token,
    session_cookie_path_from_request,
    set_session_cookie,
)


def _asgi_request(path: str) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    return Request(scope)


def test_extract_prefers_cookie_over_authorization(monkeypatch):
    monkeypatch.setattr(settings.auth, "session_cookie_enabled", True)
    monkeypatch.setattr(settings.auth, "session_cookie_name", "Authorization")
    monkeypatch.setattr(settings.auth, "token_name", "Authorization")

    request = MagicMock()
    request.cookies = {"Authorization": "cookie-token"}
    request.headers = {"Authorization": "header-token"}

    assert extract_session_token(request) == "cookie-token"


def test_extract_rejects_bearer_scheme(monkeypatch):
    monkeypatch.setattr(settings.auth, "session_cookie_enabled", True)
    monkeypatch.setattr(settings.auth, "session_cookie_name", "Authorization")
    monkeypatch.setattr(settings.auth, "token_name", "Authorization")

    request = MagicMock()
    request.cookies = {}
    request.headers = {"Authorization": "Bearer legacy-jwt"}

    assert extract_session_token(request) is None
    assert extract_session_token(request, "Bearer legacy-jwt") is None


def test_extract_raw_authorization_for_native(monkeypatch):
    monkeypatch.setattr(settings.auth, "session_cookie_enabled", True)
    monkeypatch.setattr(settings.auth, "session_cookie_name", "Authorization")
    monkeypatch.setattr(settings.auth, "token_name", "Authorization")

    request = MagicMock()
    request.cookies = {}
    request.headers = {"Authorization": "opaque-session-token"}

    assert extract_session_token(request) == "opaque-session-token"


def test_session_cookie_path_from_request_uses_parent():
    assert session_cookie_path_from_request(_asgi_request("/api/v1/admin/login")) == "/api/v1/admin"
    assert (
        session_cookie_path_from_request(_asgi_request("/api/v2/portal/logout")) == "/api/v2/portal"
    )


def test_set_session_cookie_uses_request_parent_path(monkeypatch):
    monkeypatch.setattr(settings.auth, "session_cookie_enabled", True)
    monkeypatch.setattr(settings.auth, "session_cookie_name", "Authorization")
    monkeypatch.setattr(settings.auth, "session_cookie_path", "/")
    monkeypatch.setattr(settings.auth, "session_cookie_secure", False)
    monkeypatch.setattr(settings.auth, "session_cookie_samesite", "lax")
    monkeypatch.setattr(settings.auth, "token_ttl_seconds", 3600)
    monkeypatch.setattr(settings.auth, "token_ttl_short_seconds", 600)

    response = Response()
    set_session_cookie(
        response,
        "tok-1",
        request=_asgi_request("/api/v9/admin/login"),
        remember_me=True,
    )

    set_cookie_headers = response.headers.getlist("set-cookie")
    assert any(
        "Authorization=tok-1" in item and "Path=/api/v9/admin" in item for item in set_cookie_headers
    )
    assert any(
        "Authorization=" in item and "Path=/" in item and "Max-Age=0" in item
        for item in set_cookie_headers
    )
