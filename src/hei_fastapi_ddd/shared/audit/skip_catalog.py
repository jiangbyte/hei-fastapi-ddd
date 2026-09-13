""" Author: Charlie

高频操作审计跳过表（对齐 hei-boot AuditSkipCatalog / hei-gin audit_skip.go）。
"""

from __future__ import annotations

_AUDIT_SKIP_KEYS: frozenset[str] = frozenset(
    {
        "auth:refresh",
        "auth:send_login_code",
        "auth:send_register_code",
        "sys_file:upload",
        "profile_center:upload_avatar",
        "profile_center:send_password_code",
        "profile_center:send_bind_phone_code",
        "profile_center:send_bind_email_code",
        "sys_notice:read",
        "sys_notice:read_all",
        "sys_banner:interaction",
        "real_name_case:callback",
    }
)


def _normalize_audit_key(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def should_skip_audit(resource_type: str, action: str) -> bool:
    """是否跳过操作审计入库。"""
    key = f"{_normalize_audit_key(resource_type)}:{_normalize_audit_key(action)}"
    return key in _AUDIT_SKIP_KEYS
