""" Author: Charlie """

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from hei_fastapi_ddd.contexts.sys.application.banner.banner_application_service import (
    BannerService,
)
from hei_fastapi_ddd.contexts.sys.application.banner.dto import (
    BannerCreateCommand,
    BannerPublicListQuery,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.banner_po import SysBanner
from hei_fastapi_ddd.contexts.sys.infrastructure.wiring import build_banner_service
from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum
from hei_fastapi_ddd.shared.redis.keys import banner_interaction_delta_key
from tests.conftest import FakeRedis


def _banner_create_command(**overrides) -> BannerCreateCommand:
    data = {
        "title": "Home Banner",
        "image": "https://example.com/banner.png",
        "link_url": "https://example.com",
        "category": "HOME",
        "type": "CAROUSEL",
        "position": "HOME_TOP",
        "target_account_types": ["PORTAL"],
        "sort": 10,
        "status": StatusEnum.ENABLED,
    }
    data.update(overrides)
    return BannerCreateCommand.model_validate(data)


async def _create_banner(db_session, service: BannerService, **overrides) -> str:
    await service.create(_banner_create_command(**overrides))
    title = overrides.get("title", "Home Banner")
    stmt = select(SysBanner.id).where(SysBanner.title == title)
    banner_id = (await db_session.execute(stmt)).scalar_one()
    await db_session.commit()
    return banner_id


async def test_public_banner_filters_time_status_account_type_and_sorts(db_session):
    service = build_banner_service(db_session)
    now = datetime.now(UTC)
    visible_late_id = await _create_banner(db_session, service, title="B", sort=20)
    visible_first_id = await _create_banner(db_session, service, title="A", sort=1)
    await service.create(
        _banner_create_command(title="Admin", target_account_types=["ADMIN"])
    )
    await service.create(_banner_create_command(title="Disabled", status=StatusEnum.DISABLED))
    await service.create(_banner_create_command(title="Future", start_at=now + timedelta(days=1)))
    await service.create(_banner_create_command(title="Expired", end_at=now - timedelta(days=1)))

    items = await service.list_visible(
        BannerPublicListQuery(position="HOME_TOP"),
        account_type=AccountType.PORTAL,
    )

    assert [item["id"] for item in items] == [visible_first_id, visible_late_id]


async def test_record_interaction_writes_redis_delta(db_session, monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.sys.application.banner.banner_application_service.get_redis",
        lambda: fake_redis,
    )

    service = build_banner_service(db_session)
    banner_id = await _create_banner(db_session, service)
    await service.record_interaction(banner_id, account_type=AccountType.PORTAL)

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

    flushed = await build_banner_service(db_session).flush_interaction_deltas(fake_redis)
    await db_session.refresh(banner)

    assert flushed == 1
    assert banner.interaction_count == 5
    assert fake_redis.hashes[banner_interaction_delta_key()] == {}


async def test_flush_interaction_deltas_updates_multiple_banners_in_one_statement(db_session):
    fake_redis = FakeRedis()
    first = SysBanner(
        title="First",
        image="https://example.com/1.png",
        category="home",
        type="carousel",
        position="home_top",
        target_account_types=["PORTAL"],
        interaction_count=1,
    )
    second = SysBanner(
        title="Second",
        image="https://example.com/2.png",
        category="home",
        type="carousel",
        position="home_top",
        target_account_types=["PORTAL"],
        interaction_count=4,
    )
    db_session.add_all([first, second])
    await db_session.commit()
    fake_redis.hashes[banner_interaction_delta_key()] = {first.id: "2", second.id: "5"}

    flushed = await build_banner_service(db_session).flush_interaction_deltas(fake_redis)
    await db_session.refresh(first)
    await db_session.refresh(second)

    assert flushed == 2
    assert first.interaction_count == 3
    assert second.interaction_count == 9
    assert fake_redis.hashes[banner_interaction_delta_key()] == {}
