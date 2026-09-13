""" Author: Charlie """

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import hei_fastapi_ddd.db_models  # noqa: F401 — 注册全部 ORM 元数据
from hei_fastapi_ddd.factory import create_app
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.session import close_engine
from tests.db_support import resolve_test_db_url


def _test_db_url() -> str:
    """测试库 URL：默认与 DB__URL 相同。"""
    return resolve_test_db_url()


async def _ensure_schema(engine) -> None:
    """仅补齐缺失表，不 drop、不 truncate 已有数据。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}
        self.sets: dict[str, set[object]] = {}
        self.hashes: dict[str, dict[object, str]] = {}
        self.published: list[tuple[str, object]] = []
        self._pubsubs: list[FakePubSub] = []

    async def setex(self, key: object, ttl: int, value: object) -> None:
        self.values[str(key)] = value

    async def set(
        self,
        key: object,
        value: object,
        *,
        nx: bool = False,
        xx: bool = False,
        ex: int | None = None,
        px: int | None = None,
        **_: object,
    ) -> bool | None:
        key_s = str(key)
        exists = key_s in self.values
        if nx and exists:
            return False
        if xx and not exists:
            return False
        self.values[key_s] = value
        # FakeRedis 忽略 TTL；expire() 为空操作且返回成功。
        _ = ex or px
        return True

    async def get(self, key: object) -> object | None:
        return self.values.get(str(key))

    async def getdel(self, key: object) -> object | None:
        key_s = str(key)
        value = self.values.get(key_s)
        if value is not None:
            self.values.pop(key_s, None)
        return value

    async def delete(self, key: object) -> None:
        self.values.pop(str(key), None)

    async def expire(self, key: object, seconds: int) -> bool:
        _ = seconds
        return str(key) in self.values

    async def lpush(self, key: object, *values: object) -> int:
        key_s = str(key)
        lst = self.values.setdefault(key_s, [])
        if not isinstance(lst, list):
            lst = []
            self.values[key_s] = lst
        for value in values:
            lst.insert(0, value)
        return len(lst)

    async def rpush(self, key: object, *values: object) -> int:
        key_s = str(key)
        lst = self.values.setdefault(key_s, [])
        if not isinstance(lst, list):
            lst = []
            self.values[key_s] = lst
        for value in values:
            lst.append(value)
        return len(lst)

    async def lpop(self, key: object) -> object | None:
        lst = self.values.get(str(key))
        if not isinstance(lst, list) or not lst:
            return None
        return lst.pop(0)

    async def rpop(self, key: object) -> object | None:
        lst = self.values.get(str(key))
        if not isinstance(lst, list) or not lst:
            return None
        return lst.pop()

    async def ltrim(self, key: object, start: int, end: int) -> bool:
        lst = self.values.get(str(key))
        if not isinstance(lst, list):
            return True
        # Redis 的 end 含边界；Python 切片 end 不含边界。
        if end == -1:
            self.values[str(key)] = lst[start:]
        else:
            self.values[str(key)] = lst[start : end + 1]
        return True

    async def llen(self, key: object) -> int:
        lst = self.values.get(str(key))
        return len(lst) if isinstance(lst, list) else 0

    async def sadd(self, key: object, *values: object) -> None:
        self.sets.setdefault(str(key), set()).update(values)

    async def smembers(self, key: object) -> set[object]:
        return set(self.sets.get(str(key), set()))

    async def srem(self, key: object, *values: object) -> None:
        existing = self.sets.get(str(key))
        if existing is None:
            return
        for value in values:
            existing.discard(value)

    async def hincrby(self, key: object, field: object, amount: int) -> int:
        hash_key = str(key)
        current = int(self.hashes.setdefault(hash_key, {}).get(field, "0"))
        next_value = current + amount
        self.hashes[hash_key][field] = str(next_value)
        return next_value

    async def hgetall(self, key: object) -> dict[object, str]:
        return dict(self.hashes.get(str(key), {}))

    async def hdel(self, key: object, *fields: object) -> int:
        existing = self.hashes.get(str(key), {})
        removed = 0
        for field in fields:
            if field in existing:
                removed += 1
                del existing[field]
        return removed

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None

    def pubsub(self) -> FakePubSub:
        pubsub = FakePubSub(self)
        self._pubsubs.append(pubsub)
        return pubsub

    async def publish(self, channel: str, message: object) -> int:
        self.published.append((channel, message))
        delivered = 0
        for pubsub in list(self._pubsubs):
            if channel in pubsub.channels:
                await pubsub.queue.put({"type": "message", "channel": channel, "data": message})
                delivered += 1
        return delivered


class FakePubSub:
    def __init__(self, redis: FakeRedis) -> None:
        self.redis = redis
        self.channels: set[str] = set()
        self.queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()

    async def subscribe(self, channel: str) -> None:
        self.channels.add(channel)

    async def unsubscribe(self, channel: str) -> None:
        self.channels.discard(channel)

    async def get_message(
        self,
        *,
        ignore_subscribe_messages: bool = True,
        timeout: float | None = None,
    ) -> dict[str, object] | None:
        try:
            if timeout is None:
                return await self.queue.get()
            return await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    async def aclose(self) -> None:
        if self in self.redis._pubsubs:
            self.redis._pubsubs.remove(self)


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch) -> FakeRedis:
    from hei_fastapi_ddd.shared.redis import redis as redis_module

    fake = FakeRedis()
    monkeypatch.setattr(redis_module, "redis_client", fake)

    async def _init_redis() -> None:
        redis_module.redis_client = fake

    async def _close_redis() -> None:
        redis_module.redis_client = None

    monkeypatch.setattr(redis_module, "init_redis", _init_redis)
    monkeypatch.setattr(redis_module, "close_redis", _close_redis)
    monkeypatch.setattr(redis_module, "get_redis", lambda: fake)
    yield fake


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session(monkeypatch) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(_test_db_url())
    await _ensure_schema(engine)
    async with engine.connect() as conn:
        await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        monkeypatch.setattr(
            "hei_fastapi_ddd.shared.config.reader.get_session_factory",
            lambda: session_factory,
        )
        async with session_factory() as session:
            yield session
        await conn.rollback()
    await engine.dispose()


@pytest.fixture
async def client(monkeypatch) -> AsyncIterator[AsyncClient]:
    # 契约测试需要 OpenAPI；生产默认关闭 Swagger。
    monkeypatch.setattr(settings.swagger, "enabled", True)
    monkeypatch.setattr(
        settings.cors,
        "allow_origins",
        [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5163",
            "http://127.0.0.1:5163",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ],
    )
    app = create_app()
    test_router = APIRouter()

    @test_router.get("/__test/error")
    async def raise_test_error() -> None:
        """测试专用异常路由，用于验证未处理异常能否被统一包装。"""
        raise RuntimeError("test unhandled error")

    app.include_router(test_router)
    engine = create_async_engine(_test_db_url())
    await _ensure_schema(engine)
    async with engine.connect() as conn:
        await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        from hei_fastapi_ddd.contexts.sys.interfaces.http import health_router as health_router_mod

        monkeypatch.setattr(health_router_mod, "get_session_factory", lambda: session_factory)

        async with session_factory() as shared_session:

            async def override_get_db_session() -> AsyncIterator[AsyncSession]:
                yield shared_session

            app.dependency_overrides[get_db_session] = override_get_db_session
            async with AsyncClient(
                transport=ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://testserver",
            ) as ac:

                async def _inject_csrf(request):
                    csrf = ac.cookies.get("HEI_CSRF")
                    if csrf and request.method.upper() not in {
                        "GET",
                        "HEAD",
                        "OPTIONS",
                        "TRACE",
                    }:
                        request.headers["X-HEI-CSRF"] = csrf

                ac.event_hooks["request"] = [_inject_csrf]
                try:
                    yield ac
                finally:
                    app.dependency_overrides.clear()
                    await close_engine()
        await conn.rollback()
    await engine.dispose()


@pytest.fixture
async def metrics_client() -> AsyncIterator[AsyncClient]:
    old_enabled = settings.observability.enabled
    old_metrics = settings.observability.metrics_enabled
    old_path = settings.observability.metrics_path
    settings.observability.enabled = True
    settings.observability.metrics_enabled = True
    settings.observability.metrics_path = "/metrics"
    app = create_app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        settings.observability.enabled = old_enabled
        settings.observability.metrics_enabled = old_metrics
        settings.observability.metrics_path = old_path
