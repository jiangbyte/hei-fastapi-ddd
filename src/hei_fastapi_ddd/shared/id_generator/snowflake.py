""" Author: Charlie

Snowflake ID 生成，worker 位按进程唯一。
"""
from __future__ import annotations

import hashlib
import logging
import os
import socket

from hei_fastapi_ddd.shared.config.settings import settings

try:
    from snowflake import SnowflakeGenerator
except ModuleNotFoundError as exc:  # pragma: no cover
    raise RuntimeError("snowflake-id package is required for ID generation") from exc

logger = logging.getLogger(__name__)


def _resolve_worker_id() -> int:
    """返回 0–31 的 worker id。

    ``ID_GENERATOR__WORKER_ID`` > 0 时使用配置值。
    ``0``（默认）从 hostname+pid（及可选 ``HOSTNAME`` / ``POD_NAME``）派生
    进程级稳定 id，避免多副本部署全部碰撞到 1。
    """
    configured = int(settings.id_generator.worker_id)
    if configured > 0:
        return configured & 0x1F
    host = (
        os.environ.get("POD_NAME") or os.environ.get("HOSTNAME") or socket.gethostname() or "host"
    )
    seed = f"{host}:{os.getpid()}"
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return digest[0] % 32


def _build_instance_id() -> int:
    """由 datacenter 与 worker 组合出 10 位实例 ID。"""
    datacenter = settings.id_generator.datacenter_id & 0x1F
    worker = _resolve_worker_id()
    instance = (datacenter << 5) | worker
    logger.info(
        "Snowflake instance_id=%s datacenter=%s worker=%s",
        instance,
        datacenter,
        worker,
    )
    return instance


_generator = SnowflakeGenerator(
    _build_instance_id(),
)


def generate_snowflake_id() -> str:
    """生成下一个雪花 ID 并返回字符串形式。"""
    return str(next(_generator))
