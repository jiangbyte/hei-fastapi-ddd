""" Author: Charlie

resolve_request_session 缓存在 request.state（middleware 与 Depends 共享）。
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from hei_fastapi_ddd.shared.security import session_auth
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.types.business import AuthenticationError


@pytest.mark.asyncio
async def test_resolve_reuses_request_state_cache(monkeypatch):
    session = SessionPayload(
        token="t1",
        account_id="a1",
        account_type="ADMIN",
        permission_keys=[],
        password_expired=False,
    )
    request = MagicMock()
    request.state = SimpleNamespace()

    get_mock = AsyncMock(return_value=session)
    monkeypatch.setattr(session_auth.session_store, "get", get_mock)
    monkeypatch.setattr(session_auth, "extract_session_token", lambda _r: "t1")
    monkeypatch.setattr(session_auth, "_validate_session_ip", lambda *_a, **_k: None)
    monkeypatch.setattr(session_auth, "_validate_session_user_agent", lambda *_a, **_k: None)
    monkeypatch.setattr(session_auth, "_touch_session_background", lambda *_a, **_k: None)
    monkeypatch.setattr(session_auth, "_bind_context", lambda *_a, **_k: None)

    first = await session_auth.resolve_request_session(request)
    second = await session_auth.resolve_request_session(request)

    assert first is session
    assert second is session
    assert get_mock.await_count == 1


@pytest.mark.asyncio
async def test_resolve_required_missing_token(monkeypatch):
    request = MagicMock()
    request.state = SimpleNamespace()
    monkeypatch.setattr(session_auth, "extract_session_token", lambda _r: None)
    with pytest.raises(AuthenticationError, match="Missing authorization token"):
        await session_auth.resolve_request_session(request, required=True)
