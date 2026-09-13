""" Author: Charlie

基于 structlog 的结构化日志（stdlib 集成）。
"""
from __future__ import annotations

import logging
from typing import Any

import structlog
from structlog.types import Processor

from hei_fastapi_ddd.shared.config.settings import settings


def _add_service_context(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """为日志事件补充服务名、版本与环境的默认字段。"""
    obs = settings.observability
    event_dict.setdefault("service", obs.service_name)
    event_dict.setdefault("service_version", obs.service_version)
    event_dict.setdefault("environment", obs.environment)
    return event_dict


def _drop_empty_values(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """过滤掉值为 None、空串或占位 ``-`` 的字段。"""
    return {
        key: value
        for key, value in event_dict.items()
        if value is not None and value != "" and value != "-"
    }


def _shared_processors() -> list[Processor]:
    """返回 structlog 共用的处理器链。"""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        _add_service_context,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _drop_empty_values,
    ]


def build_log_formatter() -> logging.Formatter:
    """配置 structlog 并返回与 stdlib 兼容的 ProcessorFormatter。"""
    shared = _shared_processors()
    renderer: Processor
    if settings.observability.log_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    structlog.configure(
        processors=[
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    return formatter
