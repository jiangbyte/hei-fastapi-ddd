""" Author: Charlie

空闲超时删除不得经 get() 再进 delete，避免无限递归。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store


@pytest.mark.asyncio
async def test_idle_timeout_delete_does_not_recurse(fake_redis, monkeypatch):
    monkeypatch.setattr(
        "hei_fastapi_ddd.shared.security.session.settings.auth.session_idle_timeout_seconds",
        60,
    )
    stale_at = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    payload = SessionPayload(
        token="idle-token-1",
        account_id="acc-1",
        account_type="ADMIN",
        last_active_at=stale_at,
    )
    await session_store.set(payload, ttl_seconds=3600)

    result = await session_store.get(payload.token)
    assert result is None
    assert await session_store._load_raw(fake_redis, payload.token) is None
