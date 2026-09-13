""" Author: Charlie """

async def test_metrics_endpoint_disabled_by_default(client):
    response = await client.get("/metrics")
    assert response.status_code == 404


async def test_request_id_header_present(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Request-Id")


async def test_metrics_endpoint_enabled(metrics_client):
    response = await metrics_client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text


async def test_ready_endpoint_shape(client):
    response = await client.get("/api/v1/internal/health/ready")
    assert response.status_code in {200, 503}
    data = response.json()
    assert data["status"] in {"ready", "not_ready"}
    if data["status"] == "ready":
        assert response.status_code == 200
    else:
        assert response.status_code == 503
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert "config_sync" in data["checks"]
    assert "storage" in data["checks"]
    assert "enabled" in data["checks"]["database"]
    assert "ok" in data["checks"]["database"]
    assert "detail" in data["checks"]["database"]


async def test_ready_endpoint_checks_required_redis(client):
    response = await client.get("/api/v1/internal/health/ready")
    data = response.json()
    assert data["checks"]["redis"]["enabled"] in {True, "true"}
    assert data["checks"]["redis"]["ok"] in {True, "true"}
    assert data["checks"]["redis"]["detail"] == "connection ok"
    # 单元环境中 storage 等不可用时整体仍可能为 503。
    assert response.status_code in {200, 503}
    if data["status"] == "ready":
        assert response.status_code == 200
    else:
        assert response.status_code == 503
