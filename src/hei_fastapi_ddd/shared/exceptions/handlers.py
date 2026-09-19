""" Author: Charlie

全局异常处理器：统一把业务异常、参数校验异常、HTTP 异常与未捕获异常
转换为平台统一错误响应（ApiErrorResponse），并记录指标与日志。

同时负责定制 OpenAPI 文档中的错误响应 schema。
"""

import logging
from collections.abc import Callable, Iterable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.observability.metrics import (
    record_app_exception,
    record_validation_error,
)
from hei_fastapi_ddd.shared.security.permission_registry import (
    ACCOUNT_TYPE_META_ATTR,
    PERMISSION_META_ATTR,
)
from hei_fastapi_ddd.shared.web.errors import api_error_response
from hei_fastapi_ddd.shared.web.schema import ApiErrorResponse
from hei_fastapi_ddd.types.base import AppError

# 认证根依赖回调集合：由应用侧装配时注册（core 不依赖业务包）。
_AUTH_ROOT_CALLABLES: set[Callable[..., object]] = set()


def register_auth_root_callable(callable_: Callable[..., object]) -> None:
    """注册"已认证会话"根依赖，用于 OpenAPI 文档识别需要认证的路由。"""
    _AUTH_ROOT_CALLABLES.add(callable_)


def _route_requires_auth(route: APIRoute) -> bool:
    """当路由（或嵌套 Depends）解析已认证会话时为 True。"""
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return False
    stack = list(dependant.dependencies or [])
    while stack:
        dependant = stack.pop()
        call = getattr(dependant, "call", None)
        if call in _AUTH_ROOT_CALLABLES:
            return True
        if call is not None and (
            hasattr(call, PERMISSION_META_ATTR) or hasattr(call, ACCOUNT_TYPE_META_ATTR)
        ):
            return True
        stack.extend(getattr(dependant, "dependencies", None) or [])
    return False


logger = logging.getLogger(__name__)


def _build_cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    allow_all = "*" in settings.cors.allow_origins
    if not origin:
        return {"Access-Control-Allow-Origin": "*"} if allow_all else {}
    if not allow_all and origin not in settings.cors.allow_origins:
        return {}

    headers = {
        "Access-Control-Allow-Origin": "*" if allow_all else origin,
        "Vary": "Origin",
    }
    if settings.cors.allow_credentials and not allow_all:
        headers["Access-Control-Allow-Credentials"] = "true"
    return headers


def _build_error_response(
    request: Request, status_code: int, code: int, message: str
) -> JSONResponse:
    """构造统一错误响应，避免各类异常处理器重复拼装响应结构。"""
    return api_error_response(
        status_code,
        message,
        code=code,
        headers=_build_cors_headers(request),
    )


def _format_validation_path(loc: Iterable[object]) -> str:
    """将 Pydantic/FastAPI 的错误路径压缩为更适合接口调用方阅读的字段路径。"""
    parts: list[str] = []
    for item in list(loc)[1:]:
        if isinstance(item, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{item}]"
            else:
                parts.append(f"[{item}]")
            continue
        parts.append(str(item))
    return ".".join(part for part in parts if part) or ""


def _build_validation_message(exc: RequestValidationError) -> str:
    """从校验异常中提取首条错误摘要，避免直接暴露框架默认 detail 数组。"""
    errors = exc.errors()
    if not errors:
        return "Validation failed"
    first_error = errors[0]
    path = _format_validation_path(first_error.get("loc", ()))
    detail = first_error.get("msg", "Validation failed")
    return f"{path}: {detail}" if path else str(detail)


def _extract_http_exception_message(exc: StarletteHTTPException) -> str:
    """读取 HTTP 异常的可读文案，屏蔽非字符串 detail 的默认透传。"""
    return exc.detail if isinstance(exc.detail, str) and exc.detail else "HTTP request error"


def _join_route_prefix(prefix: str, path: str) -> str:
    if not prefix:
        return path
    if not path:
        return prefix
    return prefix.rstrip("/") + "/" + path.lstrip("/")


def _iter_api_routes_with_prefix(
    routes: Iterable[object],
    prefix: str = "",
) -> list[tuple[str, APIRoute]]:
    """遍历嵌套 FastAPI 路由，产出 (full_path, APIRoute)。"""
    found: list[tuple[str, APIRoute]] = []
    for route in routes:
        if isinstance(route, APIRoute):
            found.append((_join_route_prefix(prefix, route.path_format), route))
            continue
        include_context = getattr(route, "include_context", None)
        nested_routes = getattr(route, "routes", None)
        if nested_routes is None:
            original = getattr(route, "original_router", None)
            nested_routes = getattr(original, "routes", None) if original is not None else None
        if nested_routes is None:
            continue
        child_prefix = prefix
        if include_context is not None:
            child_prefix = _join_route_prefix(prefix, getattr(include_context, "prefix", "") or "")
        found.extend(_iter_api_routes_with_prefix(nested_routes, child_prefix))
    return found


def customize_openapi_error_responses(app: FastAPI) -> None:
    """将文档中的通用错误响应统一替换为平台错误响应模型。"""

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        components["ApiErrorResponse"] = ApiErrorResponse.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )

        for full_path, route in _iter_api_routes_with_prefix(app.routes):
            path_item = schema.get("paths", {}).get(full_path) or schema.get("paths", {}).get(
                route.path_format
            )
            if not path_item:
                continue
            for method in route.methods or []:
                operation = path_item.get(method.lower())
                if not operation:
                    continue
                responses = operation.setdefault("responses", {})
                if "422" in responses:
                    responses["422"] = {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ApiErrorResponse"}
                            }
                        },
                    }
                responses.setdefault(
                    "500",
                    {
                        "description": "Internal Server Error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ApiErrorResponse"}
                            }
                        },
                    },
                )
                if _route_requires_auth(route):
                    responses.setdefault(
                        "401",
                        {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ApiErrorResponse"}
                                }
                            },
                        },
                    )
                    responses.setdefault(
                        "403",
                        {
                            "description": "Forbidden",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ApiErrorResponse"}
                                }
                            },
                        },
                    )
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        record_app_exception(exc.__class__.__name__)
        logger.warning(
            "Handled application error on %s %s: %s", request.method, request.url.path, exc.message
        )
        return _build_error_response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        record_validation_error()
        logger.warning("Validation error on %s %s", request.method, request.url.path)
        return _build_error_response(request, 422, 422, _build_validation_message(exc))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        record_app_exception(exc.__class__.__name__)
        logger.warning(
            "Handled HTTP exception on %s %s: %s", request.method, request.url.path, exc.detail
        )
        return _build_error_response(
            request,
            exc.status_code,
            exc.status_code,
            _extract_http_exception_message(exc),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        record_app_exception(exc.__class__.__name__)
        logger.exception(
            "Unhandled exception on %s %s", request.method, request.url.path, exc_info=exc
        )
        return _build_error_response(request, 500, 500, "Internal server error")
