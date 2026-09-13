""" Author: Charlie

内部健康检查路由：存活探针与聚合各依赖可用性的就绪探针。
"""

from fastapi import APIRouter, Response
from sqlalchemy import text

from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.config.sync import get_config_sync_state
from hei_fastapi_ddd.shared.persistence.session import get_session_factory
from hei_fastapi_ddd.shared.storage.manager import get_storage

router = APIRouter()


@router.get("/v1/internal/health/live")
async def live() -> dict[str, str]:
    """存活探针，仅表示应用进程仍在运行（OpenAPI 对齐 hei-boot Map 返回）。"""
    return {"status": "live"}


@router.get("/v1/internal/health/ready")
async def ready(response: Response) -> dict[str, object]:
    """就绪探针，聚合数据库、Redis、消息队列和存储配置的可用性检查。"""
    checks: dict[str, dict[str, object]] = {
        "database": {"enabled": True, "ok": False, "detail": None},
        "redis": {"enabled": True, "ok": False, "detail": None},
        "config_sync": {"enabled": False, "ok": False, "detail": None},
        "storage": {"enabled": True, "ok": False, "detail": None},
    }
    try:
        async with get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        checks["database"]["ok"] = True
        checks["database"]["detail"] = "connection ok"
    except Exception as exc:
        checks["database"]["detail"] = _safe_detail(exc)
    redis = get_redis()
    if redis is None:
        checks["redis"]["detail"] = "redis not initialized"
    else:
        try:
            await redis.ping()
            checks["redis"]["ok"] = True
            checks["redis"]["detail"] = "connection ok"
        except Exception as exc:
            checks["redis"]["detail"] = _safe_detail(exc)
    sync_state = get_config_sync_state()
    checks["config_sync"]["enabled"] = sync_state.enabled
    checks["config_sync"]["ok"] = not sync_state.enabled or sync_state.running
    checks["config_sync"]["detail"] = (
        f"channel={sync_state.channel}, last_event_at={sync_state.last_event_at}"
        if sync_state.running
        else sync_state.last_error or "listener not running"
    )
    try:
        storage = get_storage()
        checks["storage"]["ok"] = True
        checks["storage"]["detail"] = f"{storage.__class__.__name__} configured"
    except Exception as exc:
        checks["storage"]["detail"] = _safe_detail(exc)
    overall = all(
        component["ok"]
        for component in checks.values()
        if component["enabled"]
    )
    if not overall:
        response.status_code = 503
    return {
        "status": "ready" if overall else "not_ready",
        "checks": checks,
    }


def _safe_detail(exc: Exception) -> str:
    """按调试开关决定异常详情：调试返回完整信息，否则仅返回类型名。"""
    if settings.app.debug:
        return str(exc)
    return exc.__class__.__name__
