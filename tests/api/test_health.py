"""根路径健康探测契约（对齐 ApiResponse，不依赖真实 DB/Redis）。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from hei_fastapi_ddd.app.factory import create_app


@asynccontextmanager
async def _noop_lifespan(_app) -> AsyncIterator[None]:
    """测试用空生命周期，跳过 DB/Redis 初始化。"""
    yield


@pytest.mark.asyncio
async def test_root_health() -> None:
    """根路径返回统一 ApiResponse 且服务名为 hei-fastapi-ddd。"""
    # 1. 构建应用并替换 lifespan，避免真实基础设施
    app = create_app()
    app.router.lifespan_context = _noop_lifespan
    # 2. 请求根健康探测
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/")
    # 3. 校验契约字段
    assert response.status_code == 200
    data = response.json()
    assert str(data["code"]) == "200"
    assert data["message"] == "success"
    assert data["data"]["name"] == "hei-fastapi-ddd"
