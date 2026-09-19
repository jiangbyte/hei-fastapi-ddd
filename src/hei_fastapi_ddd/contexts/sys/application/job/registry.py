""" Author: Charlie

任务处理器注册表：业务模块通过 @job_handler(key) 注册处理器，
调度引擎按 sys_job.handler 解析并执行。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeAlias

logger = logging.getLogger(__name__)

# 处理器签名：接收 params（dict 或 None），返回结果摘要字符串。
JobHandlerType: TypeAlias = Callable[[dict | None], Awaitable[str]]

HANDLERS: dict[str, JobHandlerType] = {}

_handlers_loaded = False


def job_handler(name: str) -> Callable[[JobHandlerType], JobHandlerType]:
    """装饰器：按 key 注册任务处理器（重复注册直接覆盖并告警）。"""

    def decorator(func: JobHandlerType) -> JobHandlerType:
        if name in HANDLERS:
            logger.warning("job handler %r already registered, overwriting", name)
        HANDLERS[name] = func
        return func

    return decorator


def load_handlers() -> None:
    """加载 application 侧样例处理器（幂等）。

    基础设施侧处理器由 ``infrastructure.job.registry_loader`` 加载，
    避免 application → infrastructure 依赖。
    """
    global _handlers_loaded
    if _handlers_loaded:
        return
    _handlers_loaded = True
    from hei_fastapi_ddd.contexts.sys.application.job import sample as _sample_tasks  # noqa: F401


def resolve(name: str) -> JobHandlerType | None:
    """按标识解析处理器，未注册返回 None（首次调用前兜底加载 application 处理器）。"""
    load_handlers()
    return HANDLERS.get(name)
