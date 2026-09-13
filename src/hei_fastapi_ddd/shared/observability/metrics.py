""" Author: Charlie

Prometheus 指标：定义 HTTP、异常、登录、审计、文件上传等计数器/直方图/仪表。

提供指标端点响应与各类埋点上下文管理器/记录函数。
"""

import time
from contextlib import contextmanager

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

from hei_fastapi_ddd.shared.config.settings import settings

# 全局指标注册表，所有指标统一挂载于此。
registry = CollectorRegistry()

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
    registry=registry,
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    registry=registry,
)
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Current in-flight HTTP requests",
    ["method", "path"],
    registry=registry,
)
app_exceptions_total = Counter(
    "app_exceptions_total",
    "Total application exceptions",
    ["exception_type"],
    registry=registry,
)
validation_errors_total = Counter(
    "validation_errors_total",
    "Total validation errors",
    registry=registry,
)
http_client_requests_total = Counter(
    "http_client_requests_total",
    "Total outbound HTTP client requests",
    ["method", "host", "status_code"],
    registry=registry,
)
http_client_request_duration_seconds = Histogram(
    "http_client_request_duration_seconds",
    "Outbound HTTP client request duration",
    ["method", "host"],
    registry=registry,
)
auth_login_total = Counter(
    "auth_login_total",
    "Total login attempts",
    ["account_type", "result", "reason"],
    registry=registry,
)
auth_login_lock_total = Counter(
    "auth_login_lock_total",
    "Total login lock events",
    ["account_type", "scope"],
    registry=registry,
)
operation_audit_total = Counter(
    "operation_audit_total",
    "Total operation audit events",
    ["module", "action", "result"],
    registry=registry,
)
file_upload_rejected_total = Counter(
    "file_upload_rejected_total",
    "Total rejected file uploads",
    ["reason"],
    registry=registry,
)


def metrics_enabled() -> bool:
    """判断指标采集是否开启。"""
    return settings.observability.enabled and settings.observability.metrics_enabled


def metrics_response() -> Response:
    """生成 Prometheus 文本格式的指标响应。"""
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


@contextmanager
def track_http_request(method: str, path: str):
    """HTTP 请求埋点：记录在途数、耗时与状态码计数。"""
    if not metrics_enabled():
        yield lambda status_code: None
        return
    in_progress = http_requests_in_progress.labels(method=method, path=path)
    in_progress.inc()
    start = time.perf_counter()

    def finalize(status_code: int) -> None:
        duration = time.perf_counter() - start
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)
        http_requests_total.labels(method=method, path=path, status_code=str(status_code)).inc()
        in_progress.dec()

    try:
        yield finalize
    except Exception:
        in_progress.dec()
        raise


def record_app_exception(exception_type: str) -> None:
    """记录一次应用异常。"""
    if metrics_enabled():
        app_exceptions_total.labels(exception_type=exception_type).inc()


def record_validation_error() -> None:
    """记录一次参数校验错误。"""
    if metrics_enabled():
        validation_errors_total.inc()


def record_login_attempt(account_type: str, result: str, reason: str = "none") -> None:
    """记录一次登录尝试及其结果与原因。"""
    if metrics_enabled():
        auth_login_total.labels(account_type=account_type, result=result, reason=reason).inc()


def record_login_lock(account_type: str, scope: str) -> None:
    """记录一次登录锁定事件。"""
    if metrics_enabled():
        auth_login_lock_total.labels(account_type=account_type, scope=scope).inc()


def record_operation_audit(module: str, action: str, success: bool) -> None:
    """记录一次操作审计事件及其成败。"""
    if metrics_enabled():
        operation_audit_total.labels(
            module=module,
            action=action,
            result="success" if success else "failure",
        ).inc()


def record_file_upload_rejected(reason: str) -> None:
    """记录一次被拒绝的文件上传及其原因。"""
    if metrics_enabled():
        file_upload_rejected_total.labels(reason=reason).inc()


@contextmanager
def track_http_client_request(method: str, host: str):
    """出站 HTTP 客户端请求埋点：记录耗时与状态码计数。"""
    if not metrics_enabled():
        yield lambda status_code: None
        return
    start = time.perf_counter()

    def finalize(status_code: int) -> None:
        duration = time.perf_counter() - start
        http_client_request_duration_seconds.labels(method=method, host=host).observe(duration)
        http_client_requests_total.labels(
            method=method,
            host=host,
            status_code=str(status_code),
        ).inc()

    yield finalize
