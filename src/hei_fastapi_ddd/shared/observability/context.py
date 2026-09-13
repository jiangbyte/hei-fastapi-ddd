""" Author: Charlie

请求级上下文：ContextVar 在单次请求/任务内传递追踪与账户信息，并绑定到 structlog。
"""
from __future__ import annotations

from contextvars import ContextVar

import structlog

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
account_id_ctx: ContextVar[str | None] = ContextVar("account_id", default=None)
account_type_ctx: ContextVar[str | None] = ContextVar("account_type", default=None)
trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)
span_id_ctx: ContextVar[str | None] = ContextVar("span_id", default=None)
request_path_ctx: ContextVar[str | None] = ContextVar("request_path", default=None)
request_method_ctx: ContextVar[str | None] = ContextVar("request_method", default=None)
status_code_ctx: ContextVar[int | None] = ContextVar("status_code", default=None)
duration_ms_ctx: ContextVar[float | None] = ContextVar("duration_ms", default=None)
client_ip_ctx: ContextVar[str | None] = ContextVar("client_ip", default=None)
user_agent_ctx: ContextVar[str | None] = ContextVar("user_agent", default=None)


def bind_request_log_context(**values: object) -> None:
    """将字段绑定到当前请求/任务的 structlog contextvars。"""
    cleaned = {key: value for key, value in values.items() if value not in (None, "")}
    if cleaned:
        structlog.contextvars.bind_contextvars(**cleaned)


def clear_request_log_context() -> None:
    """清空当前请求/任务绑定的 structlog 上下文。"""
    structlog.contextvars.clear_contextvars()
