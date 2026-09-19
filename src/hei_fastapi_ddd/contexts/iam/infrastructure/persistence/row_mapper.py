"""Author: Charlie

PO 行映射：仓储实现统一返回字典，避免向应用层泄漏 ORM 类型。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import inspect


def po_row(entity: Any) -> dict[str, Any]:
    """将 SQLAlchemy 实体映射为列名字典。"""
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}
