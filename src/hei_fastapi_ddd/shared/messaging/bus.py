""" Author: Charlie

框架事件总线 — 基于 blinker 的进程内事件订阅/发布。

当前使用的事件:
  - on_db_ready                         -- 数据库就绪后（lifespan）
  - on_audit_event                      -- 操作审计事件（audit queue → event_handler）
"""
from __future__ import annotations

import inspect
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from blinker import Signal

logger = logging.getLogger(__name__)

# 事件处理器类型：返回协程或 None 的可调用对象。
EventHandler = Callable[..., Coroutine[Any, Any, None] | None]

# 事件名到 blinker 信号的注册表。
_signals: dict[str, Signal] = {}


def _signal(event_name: str) -> Signal:
    """获取或创建事件信号。"""
    signal = _signals.get(event_name)
    if signal is None:
        signal = Signal(doc=f"hei event: {event_name}")
        _signals[event_name] = signal
    return signal


def subscribe(event_name: str, handler: EventHandler) -> None:
    """订阅事件：将处理器注册到该事件信号（重复订阅幂等）。"""
    _signal(event_name).connect(handler)


async def emit(event_name: str, **kwargs: Any) -> None:
    """异步发布事件，逐个调用并等待协程处理器，异常仅记录不抛出。"""
    for handler in _signal(event_name).receivers_for(None):
        try:
            result = handler(**kwargs)
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception("Error in event handler %s for event %s", handler, event_name)
