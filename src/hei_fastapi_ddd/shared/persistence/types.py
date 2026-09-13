"""Author: Charlie

数据库自定义列类型。"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.types import Text, TypeDecorator


class JsonTextList(TypeDecorator[list[str]]):
    """将 list[str] 序列化为 TEXT 列中的 JSON 数组（兼容 hei-boot TEXT 列）。"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: list[str] | None, dialect: Any) -> str | None:
        if value is None:
            return json.dumps([])
        return json.dumps(value)

    def process_result_value(self, value: str | list[str] | None, dialect: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        text = str(value).strip()
        if not text:
            return []
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed]
