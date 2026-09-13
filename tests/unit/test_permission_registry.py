""" Author: Charlie """

import json
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy import select

from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import (
    ResourceService,
)
from hei_fastapi_ddd.contexts.iam.domain.enums import ResourceType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource
from hei_fastapi_ddd.contexts.iam.interfaces.http.resource_schemas import (
    ResourceCreateRequest,
    ResourcePermissionBindRequest,
)
from hei_fastapi_ddd.factory import create_app
from hei_fastapi_ddd.shared.deps.auth import require_account_type, require_permission
from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.redis.keys import (
    permission_resource_cache_key,
    permission_resource_method_cache_key,
)
from hei_fastapi_ddd.shared.security.permission_registry import (
    ACCOUNT_TYPE_META_ATTR,
    PERMISSION_META_ATTR,
    scan_permission_registry,
    sync_permission_registry,
)
from tests.conftest import FakeRedis


@dataclass
class FakeEffectiveRoute:
    original_route: Any
    path: str
    tags: list[str]
    methods: set[str]
    dependant: Any
    summary: str | None
    endpoint: Any


class FakeIncludedRouter:
    def __init__(self, candidates: list[Any]) -> None:
        self._candidates = candidates

    def effective_candidates(self) -> list[Any]:
        return self._candidates


async def test_permission_dependency_carries_scan_metadata():
    permission_dependency = require_permission("iam:account:list")
    account_type_dependency = require_account_type(*[])

    assert getattr(permission_dependency, PERMISSION_META_ATTR) == {
        "permission_key": "iam:account:list"
    }
    assert getattr(account_type_dependency, ACCOUNT_TYPE_META_ATTR) == {"account_types": []}


def test_scan_permission_registry_collects_api_resources():
    app: FastAPI = create_app()

    items = scan_permission_registry(app)

    assert any(item.permission_key == "sys:file:upload" for item in items)
    assert any(item.permission_key == "sys:file:detail" for item in items)
    assert any(item.permission_key == "sys:file:update" for item in items)
    assert any(item.permission_key == "sys:file:delete" for item in items)
    file_page = next(item for item in items if item.permission_key == "sys:file:page")
    assert file_page.route_path == "/sys/file/page"
    assert file_page.method == "GET"
    assert file_page.resource_text == "sys:file:page[page]"


def test_scan_permission_registry_collects_fastapi_137_included_router_candidates():
    router = APIRouter()

    @router.get(
        "/files/page",
        dependencies=[Depends(require_permission("sys:file:page"))],
        summary="page",
    )
    async def page():
        return {"items": []}

    original_route = router.routes[0]
    app = FastAPI()
    app.router.routes.append(
        FakeIncludedRouter(
            [
                FakeEffectiveRoute(
                    original_route=original_route,
                    path="/api/v1/admin/files/page",
                    tags=[],
                    methods=original_route.methods,
                    dependant=original_route.dependant,
                    summary=original_route.summary,
                    endpoint=original_route.endpoint,
                )
            ]
        )
    )

    items = scan_permission_registry(app)

    assert len(items) == 1
    assert items[0].permission_key == "sys:file:page"
    assert items[0].route_path == "/files/page"
    assert items[0].method == "GET"
    assert items[0].resource_text == "sys:file:page[page]"


async def test_sync_permission_registry_writes_cache_structure(monkeypatch):
    fake_redis = FakeRedis()
    app: FastAPI = create_app()

    monkeypatch.setattr("hei_fastapi_ddd.shared.security.permission_registry.get_redis", lambda: fake_redis)

    items = await sync_permission_registry(app)
    assert items
    resource_values = json.loads(fake_redis.values[permission_resource_cache_key()])
    method_map = json.loads(fake_redis.values[permission_resource_method_cache_key()])

    assert "sys:file:page[page]" in resource_values
    assert method_map["sys:file:page[page]"] == "GET"


async def test_sync_permission_registry_refuses_empty_scan(monkeypatch):
    fake_redis = FakeRedis()
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"status": "ok"}

    monkeypatch.setattr("hei_fastapi_ddd.shared.security.permission_registry.get_redis", lambda: fake_redis)

    try:
        await sync_permission_registry(app)
    except RuntimeError as exc:
        assert str(exc) == "Permission registry scan returned 0 resources; refusing to write Redis"
    else:
        raise AssertionError("Expected empty permission registry sync to fail")

    assert permission_resource_cache_key() not in fake_redis.values
    assert permission_resource_method_cache_key() not in fake_redis.values


async def test_bind_resource_permission_requires_registered_permission_key(db_session, monkeypatch):
    fake_redis = FakeRedis()
    fake_redis.values[permission_resource_cache_key()] = json.dumps([])
    monkeypatch.setattr("hei_fastapi_ddd.shared.security.permission_registry.get_redis", lambda: fake_redis)

    service = ResourceService(db_session)
    await service.create(
        ResourceCreateRequest(
            code="iam:resource:test",
            name="test",
            resource_type=ResourceType.BUTTON,
        )
    )
    resource_id = (
        await db_session.execute(
            select(SysResource.id).where(SysResource.code == "iam:resource:test")
        )
    ).scalar_one()
    await db_session.rollback()

    try:
        await service.bind_resource_permission(
            ResourcePermissionBindRequest(
                resource_id=resource_id,
                permission_key="missing:permission",
            )
        )
    except BusinessError as exc:
        assert str(exc) == "Permission is not registered in Redis: missing:permission"
    else:
        raise AssertionError("Expected registered permission validation to fail")
