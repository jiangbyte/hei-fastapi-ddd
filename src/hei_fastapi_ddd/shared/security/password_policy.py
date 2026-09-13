""" Author: Charlie

密码策略校验——强度验证与常见密码检查，对齐等保密码复杂度要求。

所有策略参数由 ``settings.password_policy`` 驱动。
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.exceptions.business import BusinessError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# fmt: off
_COMMON_PASSWORDS: frozenset[str] = frozenset({
    "123456", "password", "12345678", "qwerty", "123456789",
    "12345", "1234", "111111", "1234567", "sunshine",
    "qwerty123", "iloveyou", "princess", "admin", "welcome",
    "666666", "abc123", "football", "123123", "monkey",
    "654321", "!@#$%^&*", "charlie", "aa123456", "donald",
    "password1", "qwerty12345", "1234567890", "letmein", "password123",
    "admin123", "passw0rd", "hello123", "test123", "root",
    "administrator", "p@ssw0rd", "qwertyuiop", "asdfghjkl", "zxcvbnm",
    "pass123", "password!", "default", "change123", "changeme",
})
# fmt: on

_HAS_UPPER = re.compile(r"[A-Z]")
_HAS_LOWER = re.compile(r"[a-z]")
_HAS_DIGIT = re.compile(r"[0-9]")
_HAS_SPECIAL = re.compile(r"[^A-Za-z0-9]")
_HAS_LETTER = re.compile(r"[A-Za-z]")


def _custom_weak_words() -> set[str]:
    """读取 ``PASSWORD_CUSTOM_WEAK_WORDS`` 配置的自定义弱密码集合。"""
    raw = config_reader.get("PASSWORD_CUSTOM_WEAK_WORDS") or ""
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _require_classes(
    *,
    has_upper: bool,
    has_lower: bool,
    has_digit: bool,
    has_special: bool,
    require_upper: bool,
    require_lower: bool,
    require_digit: bool,
    require_special: bool,
) -> None:
    """按独立开关校验字符类别要求，缺一类即抛业务错误。"""
    if require_upper and not has_upper:
        raise BusinessError("密码必须包含至少一个大写字母")
    if require_lower and not has_lower:
        raise BusinessError("密码必须包含至少一个小写字母")
    if require_digit and not has_digit:
        raise BusinessError("密码必须包含至少一个数字")
    if require_special and not has_special:
        raise BusinessError("密码必须包含至少一个特殊字符")


def _check_complexity(password: str, complexity: str, policy) -> None:
    """按 complexity 枚举执行对应的字符类别组合校验。"""
    key = (complexity or "").strip().upper()
    has_upper = bool(_HAS_UPPER.search(password))
    has_lower = bool(_HAS_LOWER.search(password))
    has_digit = bool(_HAS_DIGIT.search(password))
    has_special = bool(_HAS_SPECIAL.search(password))
    has_letter = bool(_HAS_LETTER.search(password))

    if key == "NO_LIMIT":
        return

    if key == "DIGITS_AND_LETTERS":
        if not has_digit or not has_letter:
            raise BusinessError("密码必须同时包含数字和字母")
        return

    if key == "DIGITS_AND_UPPERCASE":
        _require_classes(
            has_upper=has_upper,
            has_lower=has_lower,
            has_digit=has_digit,
            has_special=has_special,
            require_upper=True,
            require_lower=False,
            require_digit=True,
            require_special=False,
        )
        return

    if key == "DIGITS_UPPER_LOWER_SPECIAL":
        _require_classes(
            has_upper=has_upper,
            has_lower=has_lower,
            has_digit=has_digit,
            has_special=has_special,
            require_upper=True,
            require_lower=True,
            require_digit=True,
            require_special=True,
        )
        return

    if key == "TWO_OF_THREE":
        # 字母 / 数字 / 特殊字符 三者至少两类
        if sum((has_letter, has_digit, has_special)) < 2:
            raise BusinessError("密码须包含字母、数字、特殊字符中的至少两类")
        return

    if key == "THREE_OF_FOUR":
        if sum((has_upper, has_lower, has_digit, has_special)) < 3:
            raise BusinessError("密码须包含大写、小写、数字、特殊字符中的至少三类")
        return

    # 未知枚举：回退到独立 require_* 开关
    _require_classes(
        has_upper=has_upper,
        has_lower=has_lower,
        has_digit=has_digit,
        has_special=has_special,
        require_upper=policy.require_uppercase,
        require_lower=policy.require_lowercase,
        require_digit=policy.require_digit,
        require_special=policy.require_special,
    )


def _check_max_consecutive(password: str, max_consecutive: int) -> None:
    """校验连续相同字符不超过配置上限。"""
    if max_consecutive <= 0 or len(password) <= max_consecutive:
        return
    run = 1
    for i in range(1, len(password)):
        if password[i] == password[i - 1]:
            run += 1
            if run > max_consecutive:
                raise BusinessError(f"密码不能包含超过 {max_consecutive} 个连续相同字符")
        else:
            run = 1


def _is_in_builtin_or_custom(password: str) -> bool:
    """判断密码是否命中内置或自定义弱密码集合。"""
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        return True
    return lowered in _custom_weak_words()


def validate_password_strength(password: str) -> None:
    """按配置策略校验密码（同步）。

    违反首条规则时抛出带用户可读消息的 ``BusinessError``。
    常见弱密码检查覆盖内置集合 + ``PASSWORD_CUSTOM_WEAK_WORDS``；
    数据库弱密码库请使用 ``is_weak_password``。
    """
    policy = settings.password_policy

    if len(password) < policy.min_length:
        raise BusinessError(f"密码长度至少 {policy.min_length} 个字符")
    if len(password) > policy.max_length:
        raise BusinessError(f"密码长度不能超过 {policy.max_length} 个字符")

    _check_complexity(password, policy.complexity, policy)
    _check_max_consecutive(password, policy.max_consecutive_chars)

    if policy.common_password_check and _is_in_builtin_or_custom(password):
        raise BusinessError("密码过于常见，请更换")


async def is_weak_password(db: AsyncSession, password: str) -> bool:
    """异步检查密码是否命中内置/自定义弱词或弱密码库表。"""
    if _is_in_builtin_or_custom(password):
        return True
    from sqlalchemy import select

    from hei_fastapi_ddd.shared.persistence.models.sys_weak_password import SysWeakPassword

    stmt = select(SysWeakPassword.id).where(SysWeakPassword.password == password).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


def estimate_strength_level(password: str) -> int:
    """返回粗略强度分数（0–4），供前端展示。"""
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if _HAS_UPPER.search(password) and _HAS_LOWER.search(password):
        score += 1
    if _HAS_DIGIT.search(password) and _HAS_SPECIAL.search(password):
        score += 1
    return min(score, 4)
