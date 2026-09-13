""" Author: Charlie

审计日志分析器 — 检测可疑模式并生成告警（对齐 hei-boot AuditAlertJob）。

每条规则独立开关，由 settings.audit_alert 控制。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from hei_fastapi_ddd.shared.config.settings import settings
logger = logging.getLogger(__name__)

# 与 hei-boot AuditAlertJob.SENSITIVE_ACTIONS 一致。
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
    """单条告警事件：规则名、严重级别、摘要与可选详情。"""

    rule_name: str
    severity: str  # INFO / WARNING / CRITICAL
    summary: str
    details: dict | None = None
    # 冷却秒数；None 时分发器使用全局 AUDIT_ALERT_ALERT_COOLDOWN_SECONDS。
    cooldown_seconds: int | None = None


class AuditAnalyzer:
    """审计日志分析器，检查预设规则并生成告警事件。"""

    async def analyze(self, db_session) -> list[AlertEvent]:
        """执行所有已启用的分析规则，返回告警事件列表。"""
        events: list[AlertEvent] = []
        cfg = settings.audit_alert

        if cfg.rule_brute_force:
            events.extend(await self._check_audit_volume(db_session, cfg.brute_force_threshold))
        if cfg.rule_unusual_hours:
            events.extend(await self._check_unusual_hours(db_session))
        if cfg.rule_sensitive_ops:
            events.extend(await self._check_sensitive_ops(db_session))
        if cfg.rule_bulk_delete:
            events.extend(await self._check_bulk_delete(db_session, cfg.bulk_delete_threshold))
        if cfg.rule_ip_anomaly:
            events.extend(await self._check_ip_anomaly(db_session, cfg.ip_anomaly_threshold))

        return events

    async def _check_audit_volume(self, db, threshold: int) -> list[AlertEvent]:
        """暴力破解近似检测：分析窗口内审计日志总量超过阈值（Boot: audit_volume）。"""
        from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_po import SysOperationAuditLog

        window_seconds = max(60, settings.audit_alert.analysis_interval_seconds)
        since = datetime.now(UTC) - timedelta(seconds=window_seconds)
        volume = (
            await db.execute(
                select(func.count(SysOperationAuditLog.id)).where(
                    SysOperationAuditLog.created_at >= since
                )
            )
        ).scalar_one()
        volume = int(volume or 0)
        logger.info(
            "Audit volume in last %ss: %s, threshold=%s",
            window_seconds,
            volume,
            threshold,
        )
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
                    "window_minutes": max(1, window_seconds // 60),
                    "since": since.isoformat(),
                },
                cooldown_seconds=cooldown,
            )
        ]

    async def _check_unusual_hours(self, db) -> list[AlertEvent]:
        """凌晨 0-6 点的敏感操作（角色/权限变更）。"""
        from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_po import SysOperationAuditLog

        now = datetime.now(UTC)
        if now.hour > 5:
            return []
        since = now - timedelta(hours=1)
        stmt = select(SysOperationAuditLog).where(
            SysOperationAuditLog.created_at >= since,
            SysOperationAuditLog.action.in_(SENSITIVE_ACTIONS),
        )
        rows = (await db.execute(stmt)).scalars().all()
        if not rows:
            return []
        return [
            AlertEvent(
                rule_name="unusual_hours",
                severity="WARNING",
                summary=f"凌晨 {now.hour} 时检测到 {len(rows)} 次敏感操作",
                details={"count": len(rows), "actions": list({r.action for r in rows})},
            )
        ]

    async def _check_sensitive_ops(self, db) -> list[AlertEvent]:
        """检测角色授权/权限变更等敏感操作（按账户聚合）。"""
        from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_po import SysOperationAuditLog

        since = datetime.now(UTC) - timedelta(seconds=300)
        stmt = (
            select(
                SysOperationAuditLog.account_id,
                func.count(SysOperationAuditLog.id).label("cnt"),
            )
            .where(
                SysOperationAuditLog.created_at >= since,
                SysOperationAuditLog.action.in_(SENSITIVE_OPS_ACTIONS),
                SysOperationAuditLog.account_id.isnot(None),
            )
            .group_by(SysOperationAuditLog.account_id)
        )
        rows = (await db.execute(stmt)).all()
        return [
            AlertEvent(
                rule_name="sensitive_ops",
                severity="WARNING",
                summary=f"账户 {row.account_id} 执行了敏感操作 ({row.cnt} 次)",
                details={"account_id": row.account_id, "count": row.cnt},
            )
            for row in rows
        ]

    async def _check_bulk_delete(self, db, threshold: int) -> list[AlertEvent]:
        """同账户 5 分钟内大量删除操作。"""
        from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_po import SysOperationAuditLog

        since = datetime.now(UTC) - timedelta(seconds=300)
        stmt = (
            select(
                SysOperationAuditLog.account_id,
                func.count(SysOperationAuditLog.id).label("cnt"),
            )
            .where(
                SysOperationAuditLog.created_at >= since,
                SysOperationAuditLog.action == "delete",
                SysOperationAuditLog.account_id.isnot(None),
            )
            .group_by(SysOperationAuditLog.account_id)
            .having(func.count(SysOperationAuditLog.id) >= threshold)
        )
        rows = (await db.execute(stmt)).all()
        return [
            AlertEvent(
                rule_name="bulk_delete",
                severity="WARNING",
                summary=f"账户 {row.account_id} 在 5 分钟内删除了 {row.cnt} 条记录",
                details={
                    "account_id": row.account_id,
                    "count": row.cnt,
                    "threshold": threshold,
                },
            )
            for row in rows
        ]

    async def _check_ip_anomaly(self, db, threshold: int) -> list[AlertEvent]:
        """同账户 15 分钟内从多个不同 IP 成功登录。"""
        from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_po import SysOperationAuditLog

        since = datetime.now(UTC) - timedelta(seconds=900)
        stmt = (
            select(
                SysOperationAuditLog.account_id,
                func.count(func.distinct(SysOperationAuditLog.ip)).label("ip_cnt"),
            )
            .where(
                SysOperationAuditLog.created_at >= since,
                SysOperationAuditLog.action == "login",
                SysOperationAuditLog.success == True,  # noqa: E712
                SysOperationAuditLog.account_id.isnot(None),
            )
            .group_by(SysOperationAuditLog.account_id)
            .having(func.count(func.distinct(SysOperationAuditLog.ip)) >= threshold)
        )
        rows = (await db.execute(stmt)).all()
        return [
            AlertEvent(
                rule_name="ip_anomaly",
                severity="WARNING",
                summary=(
                    f"账户 {row.account_id} 在 15 分钟内从 {row.ip_cnt} 个不同 IP 登录"
                ),
                details={
                    "account_id": row.account_id,
                    "ip_count": row.ip_cnt,
                    "threshold": threshold,
                },
            )
            for row in rows
        ]


audit_analyzer = AuditAnalyzer()
