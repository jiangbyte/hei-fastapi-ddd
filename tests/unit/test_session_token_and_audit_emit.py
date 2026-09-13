""" Author: Charlie

会话 token 提取与 audit emit 冒烟测试。
"""
from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request

from hei_fastapi_ddd.shared.audit.queue import OperationAuditEvent, _record_operation_audit
from hei_fastapi_ddd.shared.security.session_token import extract_session_token


def _request(
    *, headers: dict[str, str] | None = None, cookies: dict[str, str] | None = None
) -> Request:
    header_list = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    if cookies:
        header_list.append((b"cookie", "; ".join(f"{k}={v}" for k, v in cookies.items()).encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": header_list,
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    return Request(scope)


def test_extract_token_prefers_cookie(monkeypatch):
    monkeypatch.setattr(
        "hei_fastapi_ddd.shared.security.session_token.settings.auth.session_cookie_enabled",
        True,
    )
    monkeypatch.setattr(
        "hei_fastapi_ddd.shared.security.session_token.settings.auth.session_cookie_name",
        "Authorization",
    )
    req = _request(headers={"Authorization": "hdr-token"}, cookies={"Authorization": "cookie-token"})
    assert extract_session_token(req, "hdr-token") == "cookie-token"


def test_extract_token_rejects_bearer_scheme(monkeypatch):
    monkeypatch.setattr(
        "hei_fastapi_ddd.shared.security.session_token.settings.auth.session_cookie_enabled",
        True,
    )
    monkeypatch.setattr(
        "hei_fastapi_ddd.shared.security.session_token.settings.auth.session_cookie_name",
        "Authorization",
    )
    req = _request(headers={"Authorization": "Bearer legacy"})
    assert extract_session_token(req) is None


def test_extract_token_falls_back_to_cookie(monkeypatch):
    monkeypatch.setattr(
        "hei_fastapi_ddd.shared.security.session_token.settings.auth.session_cookie_enabled",
        True,
    )
    monkeypatch.setattr(
        "hei_fastapi_ddd.shared.security.session_token.settings.auth.session_cookie_name",
        "Authorization",
    )
    req = _request(cookies={"Authorization": "cookie-token"})
    assert extract_session_token(req, None) == "cookie-token"


@pytest.mark.asyncio
async def test_record_operation_audit_awaits_emit():
    event = OperationAuditEvent(
        resource_type="resources",
        action="page",
        method="GET",
        path="/api/v1/x",
        status_code=200,
        account_id="a1",
        account_type="ADMIN",
        request_id="r1",
        ip="127.0.0.1",
        user_agent="test",
    )
    mock_emit = AsyncMock()
    with patch("hei_fastapi_ddd.shared.audit.queue.emit", mock_emit):
        await _record_operation_audit(event)
    mock_emit.assert_awaited_once_with("on_audit_event", event=event)
