""" Author: Charlie """

import pytest


@pytest.mark.asyncio
async def test_protected_api_requires_auth_without_token(client):
    response = await client.get("/api/v1/admin/sys/banners/page")
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "401"
    assert "token" in body["message"].lower() or "authorization" in body["message"].lower()


@pytest.mark.asyncio
async def test_whitelisted_login_allows_anonymous(client):
    # 缺少 captcha/body 可能 422，但不应被 auth 中间件以 401 拦截
    response = await client.post("/api/v1/admin/login", json={})
    assert response.status_code != 401


@pytest.mark.asyncio
async def test_whitelisted_health_allows_anonymous(client):
    response = await client.get("/api/v1/internal/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"
