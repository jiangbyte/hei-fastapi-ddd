""" Author: Charlie

可观测性装配：按配置初始化链路追踪，并在启用指标时挂载 /metrics 端点。
"""

from fastapi import FastAPI

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.observability.metrics import metrics_enabled, metrics_response
from hei_fastapi_ddd.shared.observability.tracing import init_tracing


def setup_observability(app: FastAPI, engine=None) -> None:
    """为应用装配可观测性：追踪初始化与指标端点。"""
    if settings.observability.enabled:
        init_tracing(app=app, engine=engine)
    if metrics_enabled():
        app.add_api_route(
            settings.observability.metrics_path,
            metrics_response,
            methods=["GET"],
            include_in_schema=False,
        )
