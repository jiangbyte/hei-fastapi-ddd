"""账号登录名规则：字母/数字/下划线，长度 3-64。"""

from __future__ import annotations

import re

ACCOUNT_LOGIN_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,64}$")


def require_account_login(account: str) -> str:
    value = (account or "").strip()
    if not value:
        raise ValueError("请输入用户名")
    if not ACCOUNT_LOGIN_PATTERN.fullmatch(value):
        raise ValueError("账号仅允许字母、数字和下划线，长度 3-64")
    return value


def sanitize_account_base(raw: str) -> str:
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch == "_").lower()
    if not cleaned:
        cleaned = "user"
    if len(cleaned) < 3:
        cleaned = cleaned + "0" * (3 - len(cleaned))
    if len(cleaned) > 48:
        cleaned = cleaned[:48]
    return cleaned
