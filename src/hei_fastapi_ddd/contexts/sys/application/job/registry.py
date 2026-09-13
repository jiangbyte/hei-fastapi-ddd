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
    """显式导入业务处理器模块，触发 @job_handler 注册（幂等）。

    调度器启动时调用一次；resolve() 首次解析前也会兜底调用，
    保证手动立即执行在未启动调度器的场景下同样可用。
    """
    global _handlers_loaded
    if _handlers_loaded:
        return
    _handlers_loaded = True
    from hei_fastapi_ddd.contexts.iam.application.account import (
        tasks as _account_tasks,  # noqa: F401
    )
    from hei_fastapi_ddd.contexts.sys.application.audit import tasks as _audit_tasks  # noqa: F401
    from hei_fastapi_ddd.contexts.sys.application.banner import tasks as _banner_tasks  # noqa: F401
    from hei_fastapi_ddd.contexts.sys.application.job import sample as _sample_tasks  # noqa: F401
    from hei_fastapi_ddd.contexts.sys.application.job import tasks as _job_tasks  # noqa: F401


def resolve(name: str) -> JobHandlerType | None:
    """按标识解析处理器，未注册返回 None（首次调用前兜底加载处理器）。"""
    load_handlers()
    return HANDLERS.get(name)
