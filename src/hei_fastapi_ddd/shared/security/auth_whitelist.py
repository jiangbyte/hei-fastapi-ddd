""" Author: Charlie

统一鉴权白名单：内置模式 + settings.auth.auth_whitelist。
"""
from __future__ import annotations

import fnmatch
import logging
from functools import lru_cache

from hei_fastapi_ddd.shared.config.enums import (
    AccountType,
    account_type_url_segment,
    account_types_with_auth_routes,
)
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.paths import api_version_glob_prefix

logger = logging.getLogger(__name__)


def _builtin_client_auth_paths() -> tuple[str, ...]:
    """按 AccountType 推导各端公开认证相关路径（版本用 v* 通配）。"""
    version_glob = api_version_glob_prefix()
    paths: list[str] = []
    for account_type in account_types_with_auth_routes():
        segment = account_type_url_segment(account_type)
        base = f"{version_glob}/{segment}"
        paths.extend(
            (
                f"{base}/captcha",
                f"{base}/password-key",
                f"{base}/login",
                f"{base}/send-login-code",
                f"{base}/forgot-password",
                f"{base}/forgot-password/phone",
                f"{base}/reset-password",
                f"{base}/reset-password/phone",
                f"{base}/public/auth-options",
                f"{base}/oauth/exchange",
                f"{base}/oauth/*/authorize",
                f"{base}/oauth/*/callback",
            )
        )
        if account_type == AccountType.PORTAL:
            paths.extend(
                (
                    f"{base}/register",
                    f"{base}/register/send-code",
                    f"{base}/oauth/wechat-mp/login",
                )
            )
    return tuple(paths)


def _builtin_portal_public_paths() -> tuple[str, ...]:
    """门户侧匿名可读业务路径（版本通配 + 账户段来自枚举）。"""
    version_glob = api_version_glob_prefix()
    portal = account_type_url_segment(AccountType.PORTAL)
    base = f"{version_glob}/{portal}"
    return (
        f"{base}/sys/banners/list",
        f"{base}/sys/banners/interaction",
        f"{base}/sys/dicts/tree",
        f"{base}/sys/resources/current",
        f"{base}/sys/notices/list",
    )


# 完整请求路径（含 /api）。支持 fnmatch 通配符 (* ? [])。
BUILTIN_AUTH_WHITELIST: tuple[str, ...] = (
    "/",
    "/docs",
    "/docs/*",
    "/redoc",
    "/openapi.json",
    "/metrics",
    f"{api_version_glob_prefix()}/public/site-footer",
    *_builtin_client_auth_paths(),
    f"{api_version_glob_prefix()}/internal/health",
    f"{api_version_glob_prefix()}/internal/health/*",
    *_builtin_portal_public_paths(),
)


@lru_cache(maxsize=1)
def get_auth_whitelist_patterns() -> tuple[str, ...]:
    configured = tuple(
        pattern.strip() for pattern in settings.auth.auth_whitelist if pattern and pattern.strip()
    )
    patterns = BUILTIN_AUTH_WHITELIST + configured
    logger.info(
        "Auth whitelist loaded: %d built-in, %d configured, %d total",
        len(BUILTIN_AUTH_WHITELIST),
        len(configured),
        len(patterns),
    )
    return patterns


def clear_auth_whitelist_cache() -> None:
    """清除白名单缓存（配置热更新后调用）。"""
    get_auth_whitelist_patterns.cache_clear()


def is_auth_whitelisted(path: str) -> bool:
    """判断请求路径是否命中鉴权白名单（支持 fnmatch 通配）。"""
    normalized = path.rstrip("/") or "/"
    candidates = {path, normalized}
    if path != normalized:
        candidates.add(normalized)
    for pattern in get_auth_whitelist_patterns():
        for candidate in candidates:
            if fnmatch.fnmatchcase(candidate, pattern):
                return True
            # 允许无尾斜杠的模式匹配目录式路径
            if pattern.endswith("/*") and fnmatch.fnmatchcase(candidate, pattern[:-2]):
                return True
    return False
