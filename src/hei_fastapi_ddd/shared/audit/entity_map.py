""" Author: Charlie

将 ORM / Pydantic / dict 转为审计快照字段（对齐 hei-boot AuditSnapshots.toMap）。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from typing import Any

from hei_fastapi_ddd.shared.audit.field_filter import to_safe_map

_SIMPLE_TYPES = (str, int, float, bool, datetime, date)


def entity_to_map(source: Any) -> dict[str, Any]:
    if source is None:
        return {}
    if isinstance(source, Mapping):
        return to_safe_map(source)
    if hasattr(source, "model_dump"):
        return to_safe_map(source.model_dump())
    table = getattr(source, "__table__", None)
    if table is not None:
        payload: dict[str, Any] = {}
        for column in table.columns:
            value = getattr(source, column.key, None)
            if _is_simple(value):
                payload[column.key] = value
        return to_safe_map(payload)
    payload = {}
    for key in dir(source):
        if key.startswith("_"):
            continue
        try:
            value = getattr(source, key)
        except Exception:
            continue
        if callable(value):
            continue
        if _is_simple(value):
            payload[key] = value
    return to_safe_map(payload)


def _is_simple(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, _SIMPLE_TYPES):
        return True
    if isinstance(value, Enum):
        return True
    if isinstance(value, (list, tuple, set, frozenset)):
        return all(_is_simple(item) for item in value)
    return False
