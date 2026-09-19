""" Author: Charlie

审计分析器单测（对齐 hei-boot AuditAlertJob 语义）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from hei_fastapi_ddd.contexts.sys.application.audit import analyzer as analyzer_mod
from hei_fastapi_ddd.contexts.sys.application.audit.analyzer import AuditAnalyzer
from hei_fastapi_ddd.shared.config.settings import settings


@pytest.fixture
def repo() -> MagicMock:
    mock = MagicMock()
    mock.count_since = AsyncMock(return_value=0)
    mock.list_sensitive_actions_since = AsyncMock(return_value=[])
    mock.count_sensitive_ops_by_account = AsyncMock(return_value=[])
    mock.count_delete_ops_by_account = AsyncMock(return_value=[])
    mock.count_login_ips_by_account = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def analyzer(repo: MagicMock) -> AuditAnalyzer:
    return AuditAnalyzer(repo=repo)


@pytest.mark.asyncio
async def test_audit_volume_below_threshold(analyzer, repo, monkeypatch):
    monkeypatch.setattr(settings.audit_alert, "analysis_interval_seconds", 60)
    monkeypatch.setattr(settings.audit_alert, "alert_cooldown_seconds", 1800)
    repo.count_since = AsyncMock(return_value=3)
    events = await analyzer._check_audit_volume(threshold=10)
    assert events == []


@pytest.mark.asyncio
async def test_audit_volume_fires_warning(analyzer, repo, monkeypatch):
    monkeypatch.setattr(settings.audit_alert, "analysis_interval_seconds", 120)
    monkeypatch.setattr(settings.audit_alert, "alert_cooldown_seconds", 1800)
    repo.count_since = AsyncMock(return_value=50)
    events = await analyzer._check_audit_volume(threshold=10)
    assert len(events) == 1
    event = events[0]
    assert event.rule_name == "audit_volume"
    assert event.severity == "WARNING"
    assert event.details["volume"] == 50
    assert event.cooldown_seconds == 1800


@pytest.mark.asyncio
async def test_sensitive_ops_groups_by_account(analyzer, repo):
    repo.count_sensitive_ops_by_account = AsyncMock(
        return_value=[
            {"account_id": "a1", "count": 3},
            {"account_id": "a2", "count": 1},
        ]
    )
    events = await analyzer._check_sensitive_ops()
    assert len(events) == 2
    assert events[0].rule_name == "sensitive_ops"
    assert "敏感操作" in events[0].summary
    assert "action" not in (events[0].details or {})


@pytest.mark.asyncio
async def test_unusual_hours_uses_boot_actions(analyzer, repo, monkeypatch):
    class _FakeDateTime:
        UTC = UTC

        @staticmethod
        def now(tz=None):
            return datetime(2026, 8, 16, 2, 0, tzinfo=UTC)

    monkeypatch.setattr(analyzer_mod, "datetime", _FakeDateTime)
    monkeypatch.setattr(analyzer_mod, "timedelta", timedelta)

    repo.list_sensitive_actions_since = AsyncMock(
        return_value=[
            {"action": "permission_grant"},
            {"action": "role_grant"},
        ]
    )
    events = await analyzer._check_unusual_hours()
    assert len(events) == 1
    assert events[0].rule_name == "unusual_hours"
    assert set(events[0].details["actions"]) == {"permission_grant", "role_grant"}


@pytest.mark.asyncio
async def test_unusual_hours_skips_daytime(analyzer, repo, monkeypatch):
    class _FakeDateTime:
        UTC = UTC

        @staticmethod
        def now(tz=None):
            return datetime(2026, 8, 16, 14, 0, tzinfo=UTC)

    monkeypatch.setattr(analyzer_mod, "datetime", _FakeDateTime)
    events = await analyzer._check_unusual_hours()
    assert events == []
    repo.list_sensitive_actions_since.assert_not_awaited()
