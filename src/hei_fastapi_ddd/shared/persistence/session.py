""" Author: Charlie

数据库会话：创建异步引擎与会话工厂，并提供获取与关闭的全局单例。

仅支持 PostgreSQL / MySQL；可观测性开启时对引擎注入链路追踪。
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.persistence.compat import dialect_name_from_url
from hei_fastapi_ddd.shared.observability.tracing import init_tracing

# 进程级全局异步引擎与会话工厂。
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None:
    """创建异步引擎与会话工厂，幂等。"""
    global engine, async_session_factory
    if engine is not None:
        return
    # 启动时校验 URL，拒绝 sqlite 等非支持方言。
    dialect_name_from_url(settings.db.url)
    engine_kwargs: dict[str, object] = {
        "echo": settings.db.echo,
        "pool_size": settings.db.pool_size,
        "max_overflow": settings.db.max_overflow,
        "pool_timeout": settings.db.pool_timeout_seconds,
        "pool_recycle": settings.db.pool_recycle_seconds,
        "pool_pre_ping": settings.db.pool_pre_ping,
    }
    engine = create_async_engine(settings.db.url, **engine_kwargs)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    if settings.observability.enabled and settings.observability.db_observability_enabled:
        init_tracing(engine=engine)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """返回会话工厂，未初始化时先初始化引擎。"""
    if async_session_factory is None:
        init_engine()
    if async_session_factory is None:
        raise RuntimeError("Database session factory is not initialized")
    return async_session_factory


async def close_engine() -> None:
    """释放引擎并清空会话工厂，幂等。"""
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None
