"""定时任务处理器（基础设施层，可使用仓储实现）。"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from hei_fastapi_ddd.contexts.sys.application.job.registry import job_handler
from hei_fastapi_ddd.contexts.sys.infrastructure.wiring import build_job_service
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.persistence.session import get_session_factory
from hei_fastapi_ddd.shared.persistence.transaction import transactional

logger = logging.getLogger(__name__)


@job_handler("sys_job_log_cleanup")
async def sys_job_log_cleanup(params: dict | None) -> str:
    retention_days = _resolve_int(params, "retentionDays", settings.job.log_retention_days)
    if retention_days <= 0:
        return "skipped: retention disabled"
    batch_size = _resolve_int(params, "batchSize", settings.job.log_batch_size)
    if batch_size <= 0:
        batch_size = 1000
    before = datetime.now(UTC) - timedelta(days=retention_days)
    factory = get_session_factory()
    async with factory() as session:
        async with transactional(session):
            deleted = await build_job_service(session).cleanup_expired_logs(before, batch_size)
    return f"deleted={deleted},retentionDays={retention_days},batchSize={batch_size}"


def _resolve_int(params: dict | None, key: str, default: int) -> int:
    if params and params.get(key) is not None:
        try:
            return int(str(params[key]).strip())
        except (TypeError, ValueError):
            pass
    return int(default)
