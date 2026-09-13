""" Author: Charlie

审计相关定时任务：告警分析、日志清理。
"""
import logging

from hei_fastapi_ddd.contexts.sys.application.audit.alert import alert_dispatcher
from hei_fastapi_ddd.contexts.sys.application.audit.analyzer import audit_analyzer
from hei_fastapi_ddd.contexts.sys.application.job.registry import job_handler
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_repository import (
    OperationAuditRepository,
)
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.persistence.session import get_session_factory
from hei_fastapi_ddd.shared.persistence.transaction import transactional

logger = logging.getLogger(__name__)


@job_handler("sys_audit_alert")
async def audit_analysis_cycle(params: dict | None) -> str:
    """审计告警分析周期任务：分析 -> 分发。"""
    if not settings.audit_alert.enabled:
        logger.info("audit alert skipped: audit alert disabled")
        return "disabled"
    dispatched = await _run_analysis()
    return f"done dispatched={dispatched}"


async def _run_analysis() -> int:
    """执行分析和分发，返回分发事件数。"""
    factory = get_session_factory()
    async with factory() as session:
        events = await audit_analyzer.analyze(session)
        if events:
            await alert_dispatcher.dispatch(session, events)
            await session.commit()
            logger.info("Audit alert: %d events dispatched", len(events))
            return len(events)
        logger.debug("Audit analysis: no events")
        return 0


@job_handler("sys_audit_log_cleanup")
async def sys_audit_log_cleanup(params: dict | None) -> str:
    """按保留天数批量清理过期登录与操作审计日志（对齐 hei-boot AuditLogCleanupJob）。"""
    login_retention_days = _resolve_int(params, "loginRetentionDays", settings.audit.login_retention_days)
    operation_retention_days = _resolve_int(
        params, "operationRetentionDays", settings.audit.operation_retention_days
    )
    batch_size = _resolve_int(params, "batchSize", settings.audit.cleanup_batch_size)
    if batch_size <= 0:
        batch_size = 1000

    deleted_login = 0
    if login_retention_days > 0:
        deleted_login = await _cleanup_login_logs(login_retention_days, batch_size)
    else:
        logger.info("sys_audit_log_cleanup skipped login logs: loginRetentionDays=%s", login_retention_days)

    deleted_operation = 0
    if operation_retention_days > 0:
        deleted_operation = await _cleanup_operation_logs(operation_retention_days, batch_size)
    else:
        logger.info(
            "sys_audit_log_cleanup skipped operation logs: operationRetentionDays=%s",
            operation_retention_days,
        )

    logger.info(
        "sys_audit_log_cleanup deletedLogin=%s deletedOperation=%s loginRetentionDays=%s "
        "operationRetentionDays=%s batchSize=%s",
        deleted_login,
        deleted_operation,
        login_retention_days,
        operation_retention_days,
        batch_size,
    )
    return (
        f"deletedLogin={deleted_login},deletedOperation={deleted_operation}"
        f",loginRetentionDays={login_retention_days}"
        f",operationRetentionDays={operation_retention_days},batchSize={batch_size}"
    )


async def _cleanup_login_logs(retention_days: int, batch_size: int) -> int:
    factory = get_session_factory()
    async with factory() as session:
        async with transactional(session):
            return await OperationAuditRepository(session).cleanup_expired_login_logs(
                retention_days=retention_days,
                batch_size=batch_size,
            )


async def _cleanup_operation_logs(retention_days: int, batch_size: int) -> int:
    factory = get_session_factory()
    async with factory() as session:
        async with transactional(session):
            return await OperationAuditRepository(session).cleanup_expired_operation_logs(
                retention_days=retention_days,
                batch_size=batch_size,
            )


def _resolve_int(params: dict | None, key: str, default: int) -> int:
    if params and params.get(key) is not None:
        try:
            return int(str(params[key]).strip())
        except (TypeError, ValueError):
            logger.info("Unparseable job param %r for key %r, fallback to settings", params, key)
    return int(default)
