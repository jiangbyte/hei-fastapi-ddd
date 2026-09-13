""" Author: Charlie

账户定时任务：清理已注销且超过保留期的账户数据。
"""

import logging

from hei_fastapi_ddd.contexts.iam.application.account.account_application_service import (
    AccountService,
)
from hei_fastapi_ddd.contexts.sys.application.job.registry import job_handler
from hei_fastapi_ddd.shared.persistence.session import get_session_factory

logger = logging.getLogger(__name__)


@job_handler("iam_account_purge_cancelled")
async def purge_cancelled_accounts(params: dict | None) -> str:
    """定时任务：清理过期注销账户（execute_param 支持 retentionDays）。"""
    retention_days = _parse_retention_days(params)
    count = await _purge_cancelled_accounts(retention_days=retention_days)
    return f"purged={count}"


def _parse_retention_days(params: dict | None) -> int | None:
    """从执行参数解析保留天数；无效则返回 None 走服务默认。"""
    if params is None:
        return None
    if isinstance(params, dict) and params.get("retentionDays") is not None:
        raw = params["retentionDays"]
    else:
        # 兼容旧纯数字传参
        raw = params
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        logger.warning("Invalid retentionDays=%r; using service default", raw)
        return None


async def _purge_cancelled_accounts(*, retention_days: int | None) -> int:
    """执行过期注销账户清理。"""
    session_factory = get_session_factory()
    async with session_factory() as session:
        count = await AccountService(session).purge_expired_cancelled_accounts(
            retention_days=retention_days
        )
        logger.info("Purged expired cancelled accounts", extra={"count": count})
        return count
