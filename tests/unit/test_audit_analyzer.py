""" Author: Charlie

审计分析器单测（对齐 hei-boot AuditAlertJob 语义）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.contexts.sys.application.audit import analyzer as analyzer_mod
from hei_fastapi_ddd.contexts.sys.application.audit.analyzer import AuditAnalyzer


@pytest.fixture
def analyzer() -> AuditAnalyzer:
    return AuditAnalyzer()


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _all_result(rows):
    result = MagicMock()
    result.all.return_value = rows
    return result


def _scalars_all_result(rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


@pytest.mark.asyncio
async def test_audit_volume_below_threshold(analyzer, monkeypatch):
    monkeypatch.setattr(settings.audit_alert, "analysis_interval_seconds", 60)
    monkeypatch.setattr(settings.audit_alert, "alert_cooldown_seconds", 1800)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(3))
    events = await analyzer._check_audit_volume(db, threshold=10)
    assert events == []


@pytest.mark.asyncio
async def test_audit_volume_fires_warning(analyzer, monkeypatch):
    monkeypatch.setattr(settings.audit_alert, "analysis_interval_seconds", 120)
    monkeypatch.setattr(settings.audit_alert, "alert_cooldown_seconds", 1800)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar_result(50))
    events = await analyzer._check_audit_volume(db, threshold=10)
    assert len(events) == 1
    event = events[0]
    assert event.rule_name == "audit_volume"
    assert event.severity == "WARNING"
    assert event.details["volume"] == 50
    assert event.cooldown_seconds == 1800


@pytest.mark.asyncio
async def test_sensitive_ops_groups_by_account(analyzer):
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=_all_result(
            [SimpleNamespace(account_id="a1", cnt=3), SimpleNamespace(account_id="a2", cnt=1)]
        )
    )
    events = await analyzer._check_sensitive_ops(db)
    assert len(events) == 2
    assert events[0].rule_name == "sensitive_ops"
    assert "敏感操作" in events[0].summary
    assert "action" not in (events[0].details or {})


@pytest.mark.asyncio
async def test_unusual_hours_uses_boot_actions(analyzer, monkeypatch):
    class _FakeDateTime:
        UTC = UTC

        @staticmethod
        def now(tz=None):
            return datetime(2026, 8, 16, 2, 0, tzinfo=UTC)

    monkeypatch.setattr(analyzer_mod, "datetime", _FakeDateTime)
    monkeypatch.setattr(analyzer_mod, "timedelta", timedelta)

    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=_scalars_all_result(
            [SimpleNamespace(action="permission_grant"), SimpleNamespace(action="role_grant")]
        )
    )
    events = await analyzer._check_unusual_hours(db)
    assert len(events) == 1
    assert events[0].rule_name == "unusual_hours"
    assert set(events[0].details["actions"]) == {"permission_grant", "role_grant"}


@pytest.mark.asyncio
async def test_unusual_hours_skips_daytime(analyzer, monkeypatch):
    class _FakeDateTime:
        UTC = UTC

        @staticmethod
        def now(tz=None):
            return datetime(2026, 8, 16, 14, 0, tzinfo=UTC)

    monkeypatch.setattr(analyzer_mod, "datetime", _FakeDateTime)
    db = AsyncMock()
    events = await analyzer._check_unusual_hours(db)
    assert events == []
    db.execute.assert_not_called()
