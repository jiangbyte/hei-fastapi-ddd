""" Author: Charlie

系统配置相关 Schema：创建/更新/分页查询、批量保存与分类查询。
"""

from datetime import datetime
from typing import Any

from pydantic import Field

from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt
from hei_fastapi_ddd.shared.web.pagination import PageQuery


class ConfigCreateRequest(ApiSchema):
    """系统配置创建请求。"""

    config_key: str = Field(min_length=1, max_length=255)
    config_value: str | None = None
    category: str | None = Field(default=None, max_length=255)
    remark: str | None = Field(default=None, max_length=255)
    sort_code: WireInt = 0
    value_type: str = Field(default="STRING", max_length=32)
    label: str | None = Field(default=None, max_length=128)
    scope: str | None = Field(default=None, max_length=32)
    scene: str | None = Field(default=None, max_length=64)
    is_builtin: WireBool = False
    ext_json: dict[str, Any] = Field(default_factory=dict)


class ConfigUpdateRequest(ConfigCreateRequest):
    """系统配置更新请求，在创建字段基础上增加主键。"""

    id: str = Field(min_length=1, max_length=64)


class ConfigAdminPageQuery(PageQuery):
    """系统配置后台分页查询参数。"""

    config_key: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=255)


class SysConfigSchema(ApiSchema):
    """系统配置响应模型。"""

    id: str
    config_key: str
    config_value: str | None = None
    category: str | None = None
    remark: str | None = None
    sort_code: WireInt
    value_type: str = "STRING"
    label: str | None = None
    scope: str | None = None
    scene: str | None = None
    is_builtin: WireBool = False
    ext_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None


class ConfigBatchItem(ApiSchema):
    """系统配置批量保存条目。"""

    config_key: str = Field(min_length=1, max_length=255)
    config_value: str | None = None
    category: str | None = Field(default=None, max_length=255)
    remark: str | None = Field(default=None, max_length=255)
    value_type: str | None = Field(default=None, max_length=32)
    label: str | None = Field(default=None, max_length=128)
    scope: str | None = Field(default=None, max_length=32)
    scene: str | None = Field(default=None, max_length=64)
    is_builtin: WireBool | None = None


class ConfigBatchSaveRequest(ApiSchema):
    """系统配置批量保存请求。"""

    items: list[ConfigBatchItem]


class CategoryQuery(ApiSchema):
    """按分类查询配置的参数。"""

    category: str | None = Field(default=None, max_length=255)
