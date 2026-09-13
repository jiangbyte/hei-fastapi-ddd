""" Author: Charlie

审计快照字段过滤（避免 snapshots / entity_map 循环依赖）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hei_fastapi_ddd.contexts.sys.infrastructure.audit_labels import SENSITIVE_KEYS


def to_safe_map(data: Mapping[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    result: dict[str, Any] = {}
    for key, value in data.items():
        if _should_skip_key(str(key)):
            continue
        if value is None:
            continue
        result[str(key)] = value
    return result


def _should_skip_key(key: str) -> bool:
    normalized = key.replace("-", "").replace("_", "").lower()
    if normalized in {"id", "createdat", "updatedat", "createdby", "updatedby"}:
        return True
    for sensitive in SENSITIVE_KEYS:
        if sensitive.replace("_", "") in normalized:
            return True
    return False
