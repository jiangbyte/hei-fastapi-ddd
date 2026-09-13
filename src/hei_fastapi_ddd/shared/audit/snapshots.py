""" Author: Charlie

业务侧写入审计前后快照（对齐 hei-boot AuditSnapshots）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hei_fastapi_ddd.shared.audit.context import (
    get_resource_id,
    get_subject,
    set_after,
    set_before,
    set_resource_id,
    set_subject,
)
from hei_fastapi_ddd.shared.audit.entity_map import entity_to_map
from hei_fastapi_ddd.shared.audit.field_filter import to_safe_map


def subject(value: str | None) -> None:
    if value and str(value).strip():
        set_subject(str(value).strip())


def resource_id(value: str | None) -> None:
    if value and str(value).strip():
        set_resource_id(str(value).strip())


def before(data: Mapping[str, Any] | None) -> None:
    payload = to_safe_map(data)
    set_before(payload)
    if not get_subject():
        subject(_resolve_subject(payload))
    if not get_resource_id():
        resource_id(_resolve_id(payload))


def after(data: Mapping[str, Any] | None) -> None:
    payload = to_safe_map(data)
    set_after(payload)
    if not get_subject():
        subject(_resolve_subject(payload))
    if not get_resource_id():
        resource_id(_resolve_id(payload))


def entity(source: Any) -> dict[str, Any]:
    return entity_to_map(source)


def created_entity(source: Any) -> None:
    created(entity_to_map(source))


def before_entity(source: Any) -> None:
    before(entity_to_map(source))


def after_entity(source: Any) -> None:
    after(entity_to_map(source))


def deleted_entity(source: Any) -> None:
    deleted(entity_to_map(source))


def deleted_all(entities: list[Any]) -> None:
    if not entities:
        return
    maps = [entity_to_map(item) for item in entities]
    first = maps[0] if maps else {}
    names: list[str] = []
    ids: list[str] = []
    for item in maps:
        name = _resolve_subject(item)
        if name:
            names.append(name)
        item_id = _resolve_id(item)
        if item_id:
            ids.append(item_id)
    set_before(first)
    set_after({})
    if names:
        set_subject("，".join(names))
    if ids:
        set_resource_id(",".join(ids))


def created(data: Mapping[str, Any] | None) -> None:
    payload = to_safe_map(data)
    set_before({})
    set_after(payload)
    subject(_resolve_subject(payload))
    resource_id(_resolve_id(payload))


def deleted(data: Mapping[str, Any] | None) -> None:
    payload = to_safe_map(data)
    set_before(payload)
    set_after({})
    subject(_resolve_subject(payload))
    resource_id(_resolve_id(payload))


def _resolve_subject(data: Mapping[str, Any]) -> str | None:
    for key in (
        "name",
        "title",
        "label",
        "account",
        "code",
        "username",
        "nickname",
        "original_name",
        "originalName",
        "file_name",
        "fileName",
    ):
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _resolve_id(data: Mapping[str, Any]) -> str | None:
    for key in ("id", "case_id", "caseId", "account_id", "accountId"):
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None
