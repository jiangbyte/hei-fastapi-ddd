"""Author: Charlie

仓储入参规范化：统一 Mapping / Pydantic 为 dict。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def mapping_data(data: Mapping[str, Any] | Any) -> dict[str, Any]:
    """将 Mapping 或带 model_dump 的对象转为 dict。"""
    if hasattr(data, "model_dump"):
        return data.model_dump()
    return dict(data)
