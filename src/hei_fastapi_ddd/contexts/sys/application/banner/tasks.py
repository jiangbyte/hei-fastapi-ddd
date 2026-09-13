""" Author: Charlie

展示图周期任务：交互增量刷库 + 按 start_at/end_at 同步状态。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import or_, update

from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.shared.config.enums import StatusEnum
from hei_fastapi_ddd.shared.persistence.session import get_session_factory
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.banner_po import SysBanner
from hei_fastapi_ddd.contexts.sys.application.banner.banner_application_service import flush_interaction_deltas
from hei_fastapi_ddd.contexts.sys.application.job.registry import job_handler
logger = logging.getLogger(__name__)


@job_handler("sys_banner_flush_interactions")
async def flush_banner_interactions(params: dict | None) -> str:
    """周期任务：将展示图交互增量刷入数据库。"""
    try:
        count = await _flush_banner_interactions()
        return f"flushed={count}"
    except Exception:
        logger.exception("Flush banner interactions failed")
        raise


@job_handler("sys_banner_status_sync")
async def sync_banner_status(params: dict | None) -> str:
    """按 start_at / end_at 激活或过期 Banner（对齐 hei-boot bannerStatusJob）。"""
    try:
        result = await _sync_banner_status()
        return f"expired={result['expired']},activated={result['activated']}"
    except Exception:
        logger.exception("Banner status sync failed")
        raise


async def _flush_banner_interactions() -> int:
    """读取 Redis 交互增量并刷库，Redis 不可用时跳过。"""
    redis = get_redis()
    if redis is None:
        logger.info("Skip display image interaction flush because Redis is unavailable")
        return 0
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await flush_interaction_deltas(session, redis)


async def _sync_banner_status() -> dict[str, int]:
    """过期 ENABLED → DISABLED；到点且未过期的 DISABLED → ENABLED。"""
    now = datetime.now(UTC)
    session_factory = get_session_factory()
    async with session_factory() as session:
        expired_result = await session.execute(
            update(SysBanner)
            .where(
                SysBanner.status == StatusEnum.ENABLED.value,
                SysBanner.end_at.is_not(None),
                SysBanner.end_at < now,
            )
            .values(status=StatusEnum.DISABLED.value, updated_at=now)
        )
        activated_result = await session.execute(
            update(SysBanner)
            .where(
                SysBanner.status == StatusEnum.DISABLED.value,
                SysBanner.start_at.is_not(None),
                SysBanner.start_at <= now,
                or_(SysBanner.end_at.is_(None), SysBanner.end_at >= now),
            )
            .values(status=StatusEnum.ENABLED.value, updated_at=now)
        )
        await session.commit()
        expired = expired_result.rowcount or 0
        activated = activated_result.rowcount or 0
        logger.info("Banner status sync expired=%s activated=%s", expired, activated)
        return {"expired": expired, "activated": activated}
