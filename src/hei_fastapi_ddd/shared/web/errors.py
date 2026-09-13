""" Author: Charlie

统一 API 错误 JSON 体 / Starlette JSONResponse 构建器。
"""
from __future__ import annotations

from typing import Any

from starlette.responses import JSONResponse

from hei_fastapi_ddd.shared.web.schema import ApiErrorResponse


def api_error_body(code: int, message: str, data: Any = None) -> dict[str, Any]:
    """构造统一错误响应的 JSON 字典体。"""
    return ApiErrorResponse(code=code, message=message, data=data).model_dump(mode="json")


def api_error_response(
    status_code: int,
    message: str,
    *,
    code: int | None = None,
    data: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """构造统一错误 JSONResponse；code 缺省时回退为 HTTP 状态码。"""
    return JSONResponse(
        status_code=status_code,
        content=api_error_body(code if code is not None else status_code, message, data),
        headers=headers or {},
    )


async def asgi_error_response(
    scope,
    receive,
    send,
    *,
    status_code: int,
    message: str,
    code: int | None = None,
    headers: dict[str, str] | None = None,
) -> None:
    """从纯 ASGI 中间件发送统一错误响应。"""
    response = api_error_response(status_code, message, code=code, headers=headers)
    await response(scope, receive, send)
