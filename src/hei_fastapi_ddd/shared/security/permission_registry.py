""" Author: Charlie

权限资源注册表：从路由装饰器扫描 permission_key 并同步到 Redis，
供前端菜单/按钮渲染与运行时权限校验使用。

同时提供「权限未注册即拒绝」的校验入口，避免前端引用不存在的权限码。
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

from hei_fastapi_ddd.shared.config.enums import AccountType, account_type_url_segment
from hei_fastapi_ddd.shared.redis.keys import (
    permission_resource_cache_key,
    permission_resource_method_cache_key,
)
from hei_fastapi_ddd.shared.redis.redis import get_redis

logger = logging.getLogger(__name__)

_ACCOUNT_TYPE_PATH_ALTS = "|".join(account_type_url_segment(item) for item in AccountType)
_CLIENT_PATH_ALTS = f"{_ACCOUNT_TYPE_PATH_ALTS}|internal|public"

PERMISSION_KEY_PATTERN = re.compile(r"^[a-z0-9*]+(?::[a-z0-9*]+)+$")
# 绝对 OpenAPI 路径 → 业务路径，如 /api/v1/admin/sys/file/page → /sys/file/page
PERMISSION_ROUTE_PREFIX_PATTERN = re.compile(
    rf"^/api(?:/v[0-9]+)?(?:/(?:{_CLIENT_PATH_ALTS}))?(?=/|$)"
)
# 装饰器路径（未挂载全局 /api）
DECORATOR_CLIENT_PREFIX_PATTERN = re.compile(rf"^/v[0-9]+/(?:{_CLIENT_PATH_ALTS})(?=/|$)")
PERMISSION_META_ATTR = "__permission_meta__"
ACCOUNT_TYPE_META_ATTR = "__account_type_meta__"

RESOURCE_NAME_FALLBACK = "未定义接口名称"


@dataclass(slots=True)
class PermissionResource:
    """单个权限资源：权限码、名称、业务路径与 HTTP 方法。"""

    permission_key: str
    name: str
    route_path: str
    method: str

    @property
    def resource_text(self) -> str:
        """渲染为 ``permission_key[name]`` 形式供 Redis 与前端使用。"""
        return f"{self.permission_key}[{self.name}]"


def _iter_dependant_calls(dependant: Any) -> list[Any]:
    """递归收集依赖树中的全部可调用对象（含嵌套 Depends）。"""
    calls: list[Any] = []
    for dependency in getattr(dependant, "dependencies", []):
        call = getattr(dependency, "call", None)
        if call is not None:
            calls.append(call)
        calls.extend(_iter_dependant_calls(dependency))
    return calls


def _normalize_methods(route: Any) -> list[str]:
    """返回去重并排除 HEAD/OPTIONS 的 HTTP 方法列表。"""
    return sorted(
        method for method in (route.methods or set()) if method not in {"HEAD", "OPTIONS"}
    )


def normalize_route_path(path: str) -> str:
    """从路由路径剥离 ``/api``、API 版本与客户端段。"""
    normalized = path.strip() or "/"
    stripped = PERMISSION_ROUTE_PREFIX_PATTERN.sub("", normalized, count=1)
    if stripped != normalized:
        return stripped or "/"
    stripped = DECORATOR_CLIENT_PREFIX_PATTERN.sub("", normalized, count=1)
    return stripped or "/"


def normalize_permission_route_path(route: Any) -> str:
    """返回路由的业务路径（剥离 /api、版本与客户端段）。"""
    return normalize_route_path(route.path)


def _resolve_route_name(route: Any) -> str:
    """优先取路由 summary，否则取端点函数名，最后回退默认名。"""
    if route.summary:
        return route.summary
    endpoint_name = getattr(route.endpoint, "__name__", "")
    return endpoint_name or RESOURCE_NAME_FALLBACK


def _extract_permission_key(route: Any) -> str | None:
    """从路由依赖装饰器中提取首个合法 permission_key，无则返回 None。"""
    permission_keys: list[str] = []
    for call in _iter_dependant_calls(route.dependant):
        permission_meta = getattr(call, PERMISSION_META_ATTR, None)
        if not permission_meta:
            continue
        permission_key = str(permission_meta.get("permission_key", "")).strip()
        if not permission_key or not PERMISSION_KEY_PATTERN.fullmatch(permission_key):
            logger.warning(
                "Skip invalid permission key while scanning routes",
                extra={"permission_key": permission_key},
            )
            continue
        permission_keys.append(permission_key)
    if not permission_keys:
        return None
    return sorted(permission_keys)[0]


def _is_api_route_like(route: Any) -> bool:
    """判断路由是否为可直接使用的 APIRoute（或其代理包装）。"""
    return isinstance(route, APIRoute) or isinstance(
        getattr(route, "original_route", None),
        APIRoute,
    )


def _iter_api_route_candidates(routes: list[Any]) -> list[Any]:
    """展开嵌套路由，收集全部 API 路由候选。"""
    api_routes: list[Any] = []
    for route in routes:
        if _is_api_route_like(route):
            api_routes.append(route)
            continue

        effective_candidates = getattr(route, "effective_candidates", None)
        if callable(effective_candidates):
            api_routes.extend(_iter_api_route_candidates(list(effective_candidates())))
    return api_routes


def scan_permission_registry(app: FastAPI) -> list[PermissionResource]:
    resources: list[PermissionResource] = []
    seen_permission_keys: set[str] = set()

    total_routes = len(app.routes)
    api_routes = _iter_api_route_candidates(list(app.routes))
    logger.info(
        "Permission scan starting: total_routes=%d, api_routes=%d",
        total_routes,
        len(api_routes),
    )

    for route in api_routes:
        permission_key = _extract_permission_key(route)
        if not permission_key:
            # 诊断：检查为什么没找到 permission key
            dep_calls = _iter_dependant_calls(route.dependant)
            dep_count = len(dep_calls)
            if dep_count == 0:
                logger.warning(
                    "Route %s %s has ZERO dependency calls — decorator deps may not be populated",
                    route.methods,
                    route.path,
                )
            elif dep_count > 0:
                logger.debug(
                    "Route %s %s has %d dependency calls but no permission key found",
                    route.methods,
                    route.path,
                    dep_count,
                )
            continue
        methods = _normalize_methods(route)
        if not methods:
            continue
        route_path = normalize_permission_route_path(route)
        if permission_key in seen_permission_keys:
            continue
        seen_permission_keys.add(permission_key)
        resources.append(
            PermissionResource(
                permission_key=permission_key,
                name=_resolve_route_name(route),
                route_path=route_path,
                method=methods[0],
            )
        )

    logger.info(
        "Permission scan complete: found %d permission keys from %d API routes",
        len(resources),
        len(api_routes),
    )
    return sorted(resources, key=lambda item: item.permission_key)


async def sync_permission_registry(app: FastAPI) -> list[PermissionResource]:
    """扫描权限并写入 Redis；扫描为空时拒绝写入以防清空注册表。"""
    resources = scan_permission_registry(app)
    if not resources:
        api_route_count = len(_iter_api_route_candidates(list(app.routes)))
        logger.error(
            "Refusing to write empty permission registry to Redis: total_routes=%d, api_routes=%d",
            len(app.routes),
            api_route_count,
        )
        raise RuntimeError("Permission registry scan returned 0 resources; refusing to write Redis")

    redis = get_redis()
    if not redis:
        raise RuntimeError("Redis is required to sync permission registry")

    resource_key = permission_resource_cache_key()
    method_key = permission_resource_method_cache_key()
    resource_values = [resource.resource_text for resource in resources]
    method_map = {resource.resource_text: resource.method for resource in resources}

    logger.info(
        "Writing permission registry to Redis: key=%s, count=%d",
        resource_key,
        len(resource_values),
    )
    await redis.set(resource_key, json.dumps(resource_values, ensure_ascii=True))
    await redis.set(method_key, json.dumps(method_map, ensure_ascii=True))
    return resources


async def list_permission_resources() -> list[str]:
    """从 Redis 读取已注册的权限资源文本列表。"""
    redis = get_redis()
    if not redis:
        raise RuntimeError("Redis is required to read permission registry")
    raw = await redis.get(permission_resource_cache_key())
    if not raw:
        raise RuntimeError("Permission registry is not synced in Redis")
    raw_text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    return [str(item) for item in json.loads(raw_text)]


async def list_registered_permission_keys() -> set[str]:
    """从注册表资源文本中提取权限码集合。"""
    resources = await list_permission_resources()
    permission_keys: set[str] = set()
    for resource in resources:
        index = resource.find("[")
        permission_keys.add(resource[:index] if index > -1 else resource)
    return permission_keys


async def ensure_registered_permission_key(permission_key: str) -> None:
    """校验单个权限码已注册，否则抛业务错误。"""
    await ensure_registered_permission_keys([permission_key])


async def ensure_registered_permission_keys(permission_keys: list[str]) -> None:
    """批量校验权限码已注册，未注册项统一抛业务错误。"""
    unique_permission_keys = sorted({key for key in permission_keys if key})
    if not unique_permission_keys:
        return
    registered_permission_keys = await list_registered_permission_keys()
    missing_permission_keys = [
        permission_key
        for permission_key in unique_permission_keys
        if permission_key not in registered_permission_keys
    ]
    if missing_permission_keys:
        from hei_fastapi_ddd.shared.exceptions.business import BusinessError

        raise BusinessError(
            "Permission is not registered in Redis: " + ", ".join(missing_permission_keys)
        )
