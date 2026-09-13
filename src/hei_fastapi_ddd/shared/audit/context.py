""" Author: Charlie

请求级审计上下文（对齐 hei-boot AuditContext）。
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_before: ContextVar[dict[str, Any] | None] = ContextVar("audit_before", default=None)
_after: ContextVar[dict[str, Any] | None] = ContextVar("audit_after", default=None)
_subject: ContextVar[str | None] = ContextVar("audit_subject", default=None)
_resource_id: ContextVar[str | None] = ContextVar("audit_resource_id", default=None)


def get_before() -> dict[str, Any]:
    return dict(_before.get() or {})


def get_after() -> dict[str, Any]:
    return dict(_after.get() or {})


def get_subject() -> str | None:
    value = _subject.get()
    return value.strip() if value and value.strip() else None


def get_resource_id() -> str | None:
    value = _resource_id.get()
    return value.strip() if value and value.strip() else None


def set_before(data: dict[str, Any] | None) -> None:
    _before.set(dict(data or {}))


def set_after(data: dict[str, Any] | None) -> None:
    _after.set(dict(data or {}))


def set_subject(subject: str | None) -> None:
    if subject and str(subject).strip():
        _subject.set(str(subject).strip())
    else:
        _subject.set(None)


def set_resource_id(resource_id: str | None) -> None:
    if resource_id and str(resource_id).strip():
        _resource_id.set(str(resource_id).strip())
    else:
        _resource_id.set(None)


def clear() -> None:
    _before.set(None)
    _after.set(None)
    _subject.set(None)
    _resource_id.set(None)
