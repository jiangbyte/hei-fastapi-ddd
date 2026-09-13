""" Author: Charlie

配置跨实例同步：通过 Redis Pub/Sub 广播配置变更事件，使多实例/多进程保持一致。

提供 asyncio 监听与独立线程两种运行方式，并记录最近事件与错误。
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Thread

from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings

logger = logging.getLogger(__name__)

# 配置变更事件的 Redis 频道名。
CONFIG_SYNC_CHANNEL = "hei:config:changed"

# 本进程实例 ID，用于区分事件来源、避免回环重载。
_instance_id = uuid.uuid4().hex
_listener_task: asyncio.Task | None = None
_pubsub = None
_last_event_at: str | None = None
_last_error: str | None = None
_listener_thread: Thread | None = None
_listener_thread_loop: asyncio.AbstractEventLoop | None = None
_listener_thread_task: asyncio.Task | None = None


@dataclass(slots=True)
class ConfigSyncState:
    """配置同步运行状态快照。"""

    enabled: bool
    running: bool
    channel: str
    last_event_at: str | None = None
    last_error: str | None = None


async def reload_and_publish(reason: str) -> bool:
    """重载本进程并向其他实例发布尽力而为的配置失效事件。

    调用方须先提交写入事务（请求级 session 在鉴权查询后可能已 autobegin，
    业务 savepoint 在未 commit 前对其他连接不可见）。
    """
    await config_reader.reload()
    return await publish_config_changed(reason)


async def publish_config_changed(reason: str) -> bool:
    """向其他实例发布配置变更事件，Redis 不可用时返回 False。"""
    redis = get_redis()
    if redis is None:
        _set_error("redis not initialized")
        logger.warning("Config changed locally but Redis is unavailable; peers were not notified")
        return False

    payload = {
        "source": _instance_id,
        "reason": reason,
        "version": config_reader.version,
        "at": datetime.now(UTC).isoformat(),
    }
    try:
        await redis.publish(CONFIG_SYNC_CHANNEL, json.dumps(payload, ensure_ascii=True))
        _set_error(None)
        return True
    except Exception as exc:
        _set_error(exc.__class__.__name__)
        logger.warning("Failed to publish config change event", exc_info=True)
        return False


async def start_config_sync_listener() -> None:
    """在 asyncio 事件循环中启动配置同步监听任务，幂等。"""
    global _listener_task
    if _listener_task is not None and not _listener_task.done():
        return
    redis = get_redis()
    if redis is None:
        _set_error("redis not initialized")
        logger.warning("Config sync listener not started because Redis is unavailable")
        return
    _listener_task = asyncio.create_task(_listen(redis), name="config-sync-listener")


async def stop_config_sync_listener() -> None:
    """停止配置同步监听任务并关闭订阅。"""
    global _listener_task, _pubsub
    if _listener_task is not None:
        _listener_task.cancel()
        try:
            await _listener_task
        except asyncio.CancelledError:
            pass
        _listener_task = None
    if _pubsub is not None:
        try:
            await _pubsub.unsubscribe(CONFIG_SYNC_CHANNEL)
        except Exception:
            logger.debug("Failed to unsubscribe config sync pubsub", exc_info=True)
        await _close_pubsub()


def start_config_sync_listener_thread() -> None:
    """在 worker 进程的独立线程中启动配置同步。"""
    global _listener_thread
    if _listener_thread is not None and _listener_thread.is_alive():
        return
    _listener_thread = Thread(
        target=_run_listener_thread,
        name="config-sync-listener",
        daemon=True,
    )
    _listener_thread.start()


def stop_config_sync_listener_thread(timeout: float = 5.0) -> None:
    """停止独立线程中的配置同步监听，并等待线程退出。"""
    global _listener_thread, _listener_thread_loop, _listener_thread_task
    if _listener_thread_loop is not None and _listener_thread_task is not None:
        _listener_thread_loop.call_soon_threadsafe(_listener_thread_task.cancel)
    if _listener_thread is not None:
        _listener_thread.join(timeout=timeout)
    _listener_thread = None
    _listener_thread_loop = None
    _listener_thread_task = None


def get_config_sync_state() -> ConfigSyncState:
    """返回配置同步当前运行状态。"""
    redis = get_redis()
    running = _listener_task is not None and not _listener_task.done()
    thread_running = _listener_thread is not None and _listener_thread.is_alive()
    return ConfigSyncState(
        enabled=redis is not None or thread_running,
        running=running or thread_running,
        channel=CONFIG_SYNC_CHANNEL,
        last_event_at=_last_event_at,
        last_error=_last_error,
    )


async def _listen(redis) -> None:
    """订阅配置频道并循环处理事件；忽略本机事件，断线后重连。"""
    global _pubsub, _last_event_at
    while True:
        _pubsub = redis.pubsub()
        try:
            await _pubsub.subscribe(CONFIG_SYNC_CHANNEL)
            logger.info("Config sync listener started on channel %s", CONFIG_SYNC_CHANNEL)
            while True:
                message = await _pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
                if message is None:
                    continue
                if message.get("type") != "message":
                    continue
                event = _decode_event(message.get("data"))
                if not event or event.get("source") == _instance_id:
                    continue
                await config_reader.reload()
                _last_event_at = datetime.now(UTC).isoformat()
                _set_error(None)
                logger.info(
                    "Reloaded config from distributed event reason=%s version=%s",
                    event.get("reason"),
                    event.get("version"),
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _set_error(exc.__class__.__name__)
            logger.warning("Config sync listener reconnecting after failure", exc_info=True)
            await asyncio.sleep(5)
        finally:
            await _close_pubsub()


def _decode_event(raw: object) -> dict | None:
    """把 Pub/Sub 原始载荷解码为字典事件，非法载荷返回 None。"""
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if not isinstance(raw, str):
        return None
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return event if isinstance(event, dict) else None


def _set_error(value: str | None) -> None:
    """记录或清除最近的同步错误信息。"""
    global _last_error
    _last_error = value


async def _close_pubsub() -> None:
    """关闭并清空当前 Pub/Sub 订阅。"""
    global _pubsub
    if _pubsub is None:
        return
    try:
        close = getattr(_pubsub, "aclose", None) or getattr(_pubsub, "close", None)
        if close is not None:
            await close()
    except Exception:
        logger.debug("Failed to close config sync pubsub", exc_info=True)
    _pubsub = None


def _run_listener_thread() -> None:
    """在独立线程中创建并运行专用事件循环。"""
    global _listener_thread_loop, _listener_thread_task
    loop = asyncio.new_event_loop()
    _listener_thread_loop = loop
    asyncio.set_event_loop(loop)
    _listener_thread_task = loop.create_task(_listen_with_dedicated_redis())
    try:
        loop.run_until_complete(_listener_thread_task)
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()


async def _listen_with_dedicated_redis() -> None:
    """用独立 Redis 连接监听，结束后关闭连接。"""
    from redis.asyncio import Redis

    redis = Redis.from_url(
        settings.redis.url,
        decode_responses=False,
        max_connections=2,
    )
    try:
        await redis.ping()
        await _listen(redis)
    finally:
        await redis.aclose()
