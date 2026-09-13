""" Author: Charlie """

import asyncio
import json

from hei_fastapi_ddd.shared.config import sync as config_sync


async def test_publish_config_changed_uses_redis_channel(fake_redis):
    ok = await config_sync.publish_config_changed("unit-test")

    assert ok is True
    assert fake_redis.published
    channel, raw = fake_redis.published[-1]
    assert channel == config_sync.CONFIG_SYNC_CHANNEL
    payload = json.loads(raw)
    assert payload["reason"] == "unit-test"
    assert payload["version"] >= 0


async def test_config_sync_listener_reloads_on_peer_event(fake_redis, monkeypatch):
    reloaded = asyncio.Event()

    async def reload() -> None:
        reloaded.set()

    monkeypatch.setattr(config_sync.config_reader, "reload", reload)
    await config_sync.stop_config_sync_listener()
    await config_sync.start_config_sync_listener()
    try:
        await _wait_for_subscription(fake_redis)
        await fake_redis.publish(
            config_sync.CONFIG_SYNC_CHANNEL,
            json.dumps({"source": "peer", "reason": "sys_config.update"}),
        )
        await asyncio.wait_for(reloaded.wait(), timeout=1)
    finally:
        await config_sync.stop_config_sync_listener()


async def _wait_for_subscription(fake_redis) -> None:
    for _ in range(20):
        subscribed = any(
            config_sync.CONFIG_SYNC_CHANNEL in pubsub.channels for pubsub in fake_redis._pubsubs
        )
        if subscribed:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("config sync listener did not subscribe")
