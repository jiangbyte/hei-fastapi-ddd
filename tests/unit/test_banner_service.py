""" Author: Charlie """

from datetime import UTC, datetime, timedelta

from sqlalchemy import event, select

from hei_fastapi_ddd.shared.redis.keys import banner_interaction_delta_key
from hei_fastapi_ddd.shared.config.enums import StatusEnum
from hei_fastapi_ddd.shared.schema.base import IdQuery
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.banner_po import SysBanner
from hei_fastapi_ddd.contexts.sys.interfaces.http.banner_schemas import (
    BannerCreateRequest,
    BannerPublicListQuery,
)
from hei_fastapi_ddd.contexts.sys.application.banner.banner_application_service import BannerService, flush_interaction_deltas
from tests.conftest import FakeRedis


def _banner_create_request(**overrides) -> BannerCreateRequest:
    data = {
        "title": "Home Banner",
        "image": "https://example.com/banner.png",
        "url": "https://example.com",
        "category": "HOME",
        "type": "CAROUSEL",
        "position": "HOME_TOP",
        "target_account_types": ["PORTAL"],
        "sort": 10,
        "status": StatusEnum.ENABLED,
    }
    data.update(overrides)
    return BannerCreateRequest(**data)


async def _create_banner(db_session, service: BannerService, **overrides) -> str:
    await service.create(_banner_create_request(**overrides))
    title = overrides.get("title", "Home Banner")
    stmt = select(SysBanner.id).where(SysBanner.title == title)
    banner_id = (await db_session.execute(stmt)).scalar_one()
    await db_session.commit()
    return banner_id


async def test_public_banner_filters_time_status_account_type_and_sorts(db_session):
    service = BannerService(db_session)
    now = datetime.now(UTC)
    visible_late_id = await _create_banner(db_session, service, title="B", sort=20)
    visible_first_id = await _create_banner(db_session, service, title="A", sort=1)
    await service.create(
        _banner_create_request(title="Admin", target_account_types=["ADMIN"])
    )
    await service.create(_banner_create_request(title="Disabled", status=StatusEnum.DISABLED))
    await service.create(_banner_create_request(title="Future", start_at=now + timedelta(days=1)))
    await service.create(_banner_create_request(title="Expired", end_at=now - timedelta(days=1)))

    items = await service.list_public(BannerPublicListQuery(position="HOME_TOP"))

    assert [item.id for item in items] == [visible_first_id, visible_late_id]


async def test_record_interaction_writes_redis_delta(db_session, monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr("hei_fastapi_ddd.contexts.sys.application.banner.banner_application_service.get_redis", lambda: fake_redis)

    service = BannerService(db_session)
    banner_id = await _create_banner(db_session, service)
    await service.record_interaction(IdQuery(id=banner_id))

    assert fake_redis.hashes[banner_interaction_delta_key()][banner_id] == "1"


async def test_flush_interaction_deltas_accumulates_and_clears(db_session):
    fake_redis = FakeRedis()
    banner = SysBanner(
        title="Flush",
        image="https://example.com/flush.png",
        category="home",
        type="carousel",
        position="home_top",
        target_account_types=["PORTAL"],
        interaction_count=2,
    )
    db_session.add(banner)
    await db_session.commit()
    fake_redis.hashes[banner_interaction_delta_key()] = {banner.id: "3"}

    flushed = await flush_interaction_deltas(db_session, fake_redis)
    await db_session.refresh(banner)

    assert flushed == 1
    assert banner.interaction_count == 5
    assert fake_redis.hashes[banner_interaction_delta_key()] == {}


async def test_flush_interaction_deltas_updates_multiple_banners_in_one_statement(db_session):
    fake_redis = FakeRedis()
    first = SysBanner(
        title="Flush A",
        image="https://example.com/a.png",
        category="home",
        type="carousel",
        position="home_top",
        target_account_types=["PORTAL"],
        interaction_count=1,
    )
    second = SysBanner(
        title="Flush B",
        image="https://example.com/b.png",
        category="home",
        type="carousel",
        position="home_top",
        target_account_types=["PORTAL"],
        interaction_count=10,
    )
    db_session.add_all([first, second])
    await db_session.commit()
    fake_redis.hashes[banner_interaction_delta_key()] = {
        first.id: "2",
        second.id: "4",
    }
    update_statements: list[str] = []

    def capture_update(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("UPDATE SYS_BANNER"):
            update_statements.append(statement)

    sync_engine = db_session.bind.sync_engine
    event.listen(sync_engine, "before_cursor_execute", capture_update)
    try:
        flushed = await flush_interaction_deltas(db_session, fake_redis)
    finally:
        event.remove(sync_engine, "before_cursor_execute", capture_update)
    await db_session.refresh(first)
    await db_session.refresh(second)

    assert flushed == 2
    assert first.interaction_count == 3
    assert second.interaction_count == 14
    assert len(update_statements) == 1
