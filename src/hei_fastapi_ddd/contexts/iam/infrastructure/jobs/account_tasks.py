"""IAM 账户定时任务（基础设施入口）。"""

from __future__ import annotations

import logging

from hei_fastapi_ddd.contexts.iam.application.account.account_application_service import (
    AccountService,
)
from hei_fastapi_ddd.contexts.iam.application.account.account_read_service import AccountReadService
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import (
    AccountRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import (
    IamRelationRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.support.iam_audit_adapter import IamAuditAdapter
from hei_fastapi_ddd.contexts.profile.infrastructure.api.profile_read_adapter import (
    ProfileReadAdapter,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.api.profile_upsert_adapter import (
    ProfileUpsertAdapter,
)
from hei_fastapi_ddd.contexts.sys.application.job.registry import job_handler
from hei_fastapi_ddd.shared.persistence.session import get_session_factory

logger = logging.getLogger(__name__)


@job_handler("iam_account_purge_cancelled")
async def purge_cancelled_accounts(params: dict | None) -> str:
    """定时任务：清理过期注销账户。"""
    retention_days = _parse_retention_days(params)
    count = await _purge_cancelled_accounts(retention_days=retention_days)
    return f"purged={count}"


def _parse_retention_days(params: dict | None) -> int | None:
    if params is None:
        return None
    if isinstance(params, dict) and params.get("retentionDays") is not None:
        raw = params["retentionDays"]
    else:
        raw = params
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        logger.warning("Invalid retentionDays=%r; using service default", raw)
        return None


async def _purge_cancelled_accounts(*, retention_days: int | None) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = AccountRepositoryImpl(session)
        service = AccountService(
            session,
            repo=repo,
            profile_port=ProfileUpsertAdapter(session),
            relation_repo=IamRelationRepositoryImpl(session),
            audit=IamAuditAdapter(session),
            read_service=AccountReadService(repo, ProfileReadAdapter(session)),
        )
        count = await service.purge_expired_cancelled_accounts(retention_days=retention_days)
        logger.info("Purged expired cancelled accounts", extra={"count": count})
        return count
