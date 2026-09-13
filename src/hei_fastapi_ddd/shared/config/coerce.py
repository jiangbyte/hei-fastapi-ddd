""" Author: Charlie

配置值类型转换：将 DB 中存为字符串的配置值按 settings 字段声明的注解强制转换。

基于 ``pydantic.TypeAdapter`` 完成类型解析（支持 str/bool/int/float、list/dict
JSON 以及 Optional/枚举类型），转换失败时返回 None，由调用方跳过覆盖、保留默认值。
"""

from __future__ import annotations

import json
from typing import Any, get_origin

from pydantic import TypeAdapter


def coerce_config_value(value: Any, annotation: Any) -> Any:
    """将 DB 字符串配置值强制转换为 settings 字段声明的类型，失败返回 None。"""
    if value is None:
        return None
    try:
        return TypeAdapter(annotation).validate_python(_prepare_json(value, annotation))
    except Exception:
        return None


def _prepare_json(value: Any, annotation: Any) -> Any:
    """list/dict 注解的字符串值先按 JSON 解析，供 TypeAdapter 校验。"""
    origin = get_origin(annotation)
    if origin in (list, dict) or annotation in (list, dict):
        if isinstance(value, str):
            return json.loads(value)
    return value
