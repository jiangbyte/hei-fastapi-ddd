""" Author: Charlie

登录设置 HttpOnly 会话 cookie（cookie 优先 Web 会话）。
"""
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from hei_fastapi_ddd.app.factory import create_app
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.security.session import SessionPayload


@pytest.mark.asyncio
async def test_admin_login_sets_session_cookie(monkeypatch):
    monkeypatch.setattr(settings.auth, "session_cookie_enabled", True)
    monkeypatch.setattr(settings.auth, "session_cookie_name", "Authorization")
    monkeypatch.setattr(settings.swagger, "enabled", False)

    session = SessionPayload(
        token="tok-cookie-1",
        account_id="acc-1",
        account_type="ADMIN",
        permission_keys=[],
        password_expired=False,
    )

    async def _fake_login(self, payload):
        return session

    async def _fake_warning(self, account_id: str):
        return None

    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.auth.application.auth_application_service.AuthService.login",
        _fake_login,
    )
    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.auth.application.auth_application_service.AuthService.password_expiry_warning_days",
        _fake_warning,
    )
    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.auth.trigger.http.auth_router.verify_captcha",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.auth.trigger.http.auth_router.decrypt_password",
        AsyncMock(return_value="plain"),
    )

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/admin/login",
            json={
                "account": "admin",
                "password": "x",
                "identity_type": "ACCOUNT",
                "remember_me": True,
                "password_key_id": "k",
                "captcha_id": "c",
                "captcha_value": "1",
            },
        )

    assert response.status_code == 200
    assert response.json()["data"]["token"] == "tok-cookie-1"
    cookie = response.cookies.get("Authorization")
    assert cookie == "tok-cookie-1"
    set_cookie = ";".join(response.headers.get_list("set-cookie"))
    assert "Path=/api/v1/admin" in set_cookie
