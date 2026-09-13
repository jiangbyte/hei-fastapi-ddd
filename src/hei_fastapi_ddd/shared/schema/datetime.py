""" Author: Charlie

datetime 处理辅助：统一内部 UTC 表示与 ISO 8601 线型输出。
"""

from datetime import UTC, datetime
from typing import Any, get_args, get_origin


def ensure_utc_datetime(value: datetime) -> datetime:
    """将时间统一转换为 UTC。

    MySQL 等驱动对 ``DateTime(timezone=True)`` 常返回 naive datetime，
    与 ORM 侧 ``normalize_orm_datetimes`` 一致，视为 UTC。
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def format_utc_iso8601(value: datetime) -> str:
    """将时间序列化为 ISO 8601 UTC 字符串（微秒精度，对齐 hei-boot OffsetDateTime）。"""
    value = ensure_utc_datetime(value)
    base = value.strftime("%Y-%m-%dT%H:%M:%S")
    if value.microsecond:
        frac = f"{value.microsecond:06d}".rstrip("0")
        return f"{base}.{frac}Z"
    return f"{base}Z"


def normalize_orm_datetimes(item: object) -> None:
    """将 ORM 对象中已加载的 naive datetime 视为 UTC（不触发惰性加载）。"""
    values = getattr(item, "__dict__", None)
    if not isinstance(values, dict):
        return
    for field_name, value in list(values.items()):
        if field_name.startswith("_"):
            continue
        if isinstance(value, datetime) and (value.tzinfo is None or value.utcoffset() is None):
            setattr(item, field_name, value.replace(tzinfo=UTC))


def is_datetime_annotation(annotation: Any) -> bool:
    """判断字段注解是否为 datetime 或包含 datetime 的联合类型。"""
    if annotation is datetime:
        return True
    origin = get_origin(annotation)
    if origin is None:
        return False
    return datetime in get_args(annotation)
