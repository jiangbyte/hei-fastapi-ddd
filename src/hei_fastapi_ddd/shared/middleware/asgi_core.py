""" Author: Charlie

标准 Trace / AuthContext / AccessLog 中间件（纯 ASGI）。

factory 从此处与 ``asgi_rest`` 导入，不再提供薄 re-export 垫片。
"""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from hei_fastapi_ddd.shared.network.client_ip import get_client_ip
from hei_fastapi_ddd.shared.observability.context import (
    account_id_ctx,
    account_type_ctx,
    bind_request_log_context,
    clear_request_log_context,
    client_ip_ctx,
    duration_ms_ctx,
    request_id_ctx,
    request_method_ctx,
    request_path_ctx,
    span_id_ctx,
    status_code_ctx,
    trace_id_ctx,
    user_agent_ctx,
)
from hei_fastapi_ddd.shared.observability.metrics import track_http_request
from hei_fastapi_ddd.shared.observability.tracing import sync_trace_context

logger = structlog.get_logger("access")


class TraceMiddleware:
    """Trace 中间件：注入 request_id / trace_id 等追踪上下文，并在响应头回写 x-request-id。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """为 HTTP 请求建立追踪上下文并透传响应头。"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        request_id = headers.get("x-request-id") or uuid.uuid4().hex
        request = Request(scope, receive)
        client_ip = get_client_ip(request)
        user_agent = headers.get("user-agent")
        path = scope.get("path") or ""
        method = scope.get("method") or ""

        request_token = request_id_ctx.set(request_id)
        path_token = request_path_ctx.set(path)
        method_token = request_method_ctx.set(method)
        ip_token = client_ip_ctx.set(client_ip)
        user_agent_token = user_agent_ctx.set(user_agent)

        clear_request_log_context()
        bind_request_log_context(
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        try:
            sync_trace_context()
            bind_request_log_context(
                trace_id=trace_id_ctx.get(),
                span_id=span_id_ctx.get(),
            )

            async def send_wrapper(message: Message) -> None:
                if message["type"] == "http.response.start":
                    headers_list = list(message.get("headers") or [])
                    headers_list.append((b"x-request-id", request_id.encode()))
                    message = {**message, "headers": headers_list}
                await send(message)

            await self.app(scope, receive, send_wrapper)
        finally:
            clear_request_log_context()
            request_id_ctx.reset(request_token)
            request_path_ctx.reset(path_token)
            request_method_ctx.reset(method_token)
            client_ip_ctx.reset(ip_token)
            user_agent_ctx.reset(user_agent_token)
            trace_id_ctx.set(None)
            span_id_ctx.set(None)


class AuthContextMiddleware:
    """认证上下文中间件：初始化账户与状态相关的 ContextVar，并在请求结束后重置。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """初始化账户/状态上下文并在结束后重置。"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        account_token = account_id_ctx.set(None)
        account_type_token = account_type_ctx.set(None)
        status_token = status_code_ctx.set(None)
        duration_token = duration_ms_ctx.set(None)
        try:
            await self.app(scope, receive, send)
        finally:
            account_id_ctx.reset(account_token)
            account_type_ctx.reset(account_type_token)
            status_code_ctx.reset(status_token)
            duration_ms_ctx.reset(duration_token)


class AccessLogMiddleware:
    """访问日志中间件：记录 HTTP 状态码、耗时并上报指标。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """包裹下游应用，记录状态码、耗时并上报指标。"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        path = scope.get("path") or ""
        method = scope.get("method") or ""
        status_code = 500
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                status_code = int(message.get("status") or 500)
                response_started = True
            await send(message)

        with track_http_request(method, path) as finalize:
            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                final_status = status_code if response_started else 500
                cost_ms = round((time.perf_counter() - start) * 1000, 2)
                duration_ms_ctx.set(cost_ms)
                status_code_ctx.set(final_status)
                finalize(final_status)
                logger.info(
                    "http.access",
                    request_id=request_id_ctx.get(),
                    method=method,
                    path=path,
                    status_code=final_status,
                    duration_ms=cost_ms,
                    client_ip=client_ip_ctx.get(),
                    user_agent=user_agent_ctx.get(),
                )
