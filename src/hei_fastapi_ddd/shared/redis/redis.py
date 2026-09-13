""" Author: Charlie

Redis 客户端：基于 redis-py 的异步连接池，提供初始化、获取与关闭的全局单例。

连接参数对齐 Redisson 的 keepalive 意图，尽力配置 TCP keepalive 选项。
"""

import logging
import socket

from redis.asyncio import Redis

from hei_fastapi_ddd.shared.config.settings import settings

logger = logging.getLogger(__name__)

# 进程级全局 Redis 客户端；未初始化时为 None。
redis_client: Redis | None = None


def _keepalive_options() -> dict[int, int]:
    """尽力配置 TCP keepalive 选项（Linux/BSD；Windows 可能忽略）。"""
    opts: dict[int, int] = {}
    if hasattr(socket, "TCP_KEEPIDLE"):
        opts[socket.TCP_KEEPIDLE] = 60
    if hasattr(socket, "TCP_KEEPINTVL"):
        opts[socket.TCP_KEEPINTVL] = 10
    if hasattr(socket, "TCP_KEEPCNT"):
        opts[socket.TCP_KEEPCNT] = 3
    return opts


async def init_redis() -> None:
    """初始化 Redis 客户端并 ping 验证连接，幂等。"""
    global redis_client
    if redis_client is not None:
        return
    # 通过 redis-py 连接参数对齐 Redisson keepAlive 意图。
    kwargs: dict = {
        "decode_responses": False,
        "max_connections": settings.redis.max_connections,
        "socket_keepalive": True,
    }
    keepalive = _keepalive_options()
    if keepalive:
        kwargs["socket_keepalive_options"] = keepalive
    redis_client = Redis.from_url(settings.redis.url, **kwargs)
    await redis_client.ping()
    logger.info("Redis connected (socket_keepalive=True)")


def get_redis() -> Redis | None:
    """返回全局 Redis 客户端，未初始化时返回 None。"""
    return redis_client


async def close_redis() -> None:
    """关闭并清空全局 Redis 客户端，幂等。"""
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
