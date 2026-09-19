"""审计日志分析器 — 检测可疑模式并生成告警。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from hei_fastapi_ddd.contexts.sys.domain.audit.repository import AuditAnalysisRepository
from hei_fastapi_ddd.shared.config.settings import settings

logger = logging.getLogger(__name__)

SENSITIVE_ACTIONS = (
    "role_create",
    "role_grant",
    "permission_change",
    "permission_grant",
)

SENSITIVE_OPS_ACTIONS = (
    "role_grant",
    "permission_change",
    "permission_grant",
)


@dataclass(frozen=True, slots=True)
class AlertEvent:
    """单条告警事件。"""

    rule_name: str
    severity: str
    summary: str
    details: dict | None = None
    cooldown_seconds: int | None = None


class AuditAnalyzer:
    """审计日志分析器。"""

    def __init__(self, repo: AuditAnalysisRepository):
        self._repo = repo

    async def analyze(self) -> list[AlertEvent]:
        """执行所有已启用的分析规则。"""
        events: list[AlertEvent] = []
        cfg = settings.audit_alert
        if cfg.rule_brute_force:
            events.extend(await self._check_audit_volume(cfg.brute_force_threshold))
        if cfg.rule_unusual_hours:
            events.extend(await self._check_unusual_hours())
        if cfg.rule_sensitive_ops:
            events.extend(await self._check_sensitive_ops())
        if cfg.rule_bulk_delete:
            events.extend(await self._check_bulk_delete(cfg.bulk_delete_threshold))
        if cfg.rule_ip_anomaly:
            events.extend(await self._check_ip_anomaly(cfg.ip_anomaly_threshold))
        return events

    async def _check_audit_volume(self, threshold: int) -> list[AlertEvent]:
        window_seconds = max(60, settings.audit_alert.analysis_interval_seconds)
        since = datetime.now(UTC) - timedelta(seconds=window_seconds)
        volume = await self._repo.count_since(since)
        if volume < threshold:
            return []
        cooldown = max(window_seconds, settings.audit_alert.alert_cooldown_seconds)
        return [
            AlertEvent(
                rule_name="audit_volume",
                severity="WARNING",
                summary=(
                    f"Audit log volume {volume} exceeded threshold {threshold} "
                    f"in last {window_seconds} seconds"
                ),
                details={
                    "volume": volume,
                    "threshold": threshold,
                    "window_seconds": window_seconds,
                    "since": since.isoformat(),
                },
                cooldown_seconds=cooldown,
            )
        ]

    async def _check_unusual_hours(self) -> list[AlertEvent]:
        now = datetime.now(UTC)
        if now.hour > 5:
            return []
        since = now - timedelta(hours=1)
        rows = await self._repo.list_sensitive_actions_since(since, SENSITIVE_ACTIONS)
        if not rows:
            return []
        actions = list({r["action"] for r in rows})
        return [
            AlertEvent(
                rule_name="unusual_hours",
                severity="WARNING",
                summary=f"凌晨 {now.hour} 时检测到 {len(rows)} 次敏感操作",
                details={"count": len(rows), "actions": actions},
            )
        ]

    async def _check_sensitive_ops(self) -> list[AlertEvent]:
        since = datetime.now(UTC) - timedelta(seconds=300)
        rows = await self._repo.count_sensitive_ops_by_account(since, SENSITIVE_OPS_ACTIONS)
        return [
            AlertEvent(
                rule_name="sensitive_ops",
                severity="WARNING",
                summary=f"账户 {row['account_id']} 执行了敏感操作 ({row['count']} 次)",
                details={"account_id": row["account_id"], "count": row["count"]},
            )
            for row in rows
        ]

    async def _check_bulk_delete(self, threshold: int) -> list[AlertEvent]:
        since = datetime.now(UTC) - timedelta(seconds=300)
        rows = await self._repo.count_delete_ops_by_account(since, threshold)
        return [
            AlertEvent(
                rule_name="bulk_delete",
                severity="WARNING",
                summary=f"账户 {row['account_id']} 在 5 分钟内删除了 {row['count']} 条记录",
                details=row,
            )
            for row in rows
        ]

    async def _check_ip_anomaly(self, threshold: int) -> list[AlertEvent]:
        since = datetime.now(UTC) - timedelta(seconds=900)
        rows = await self._repo.count_login_ips_by_account(since, threshold)
        return [
            AlertEvent(
                rule_name="ip_anomaly",
                severity="WARNING",
                summary=(
                    f"账户 {row['account_id']} 在 15 分钟内从 {row['ip_count']} 个不同 IP 登录"
                ),
                details=row,
            )
            for row in rows
        ]
