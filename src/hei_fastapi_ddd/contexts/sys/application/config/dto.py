"""系统配置应用层 DTO。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from hei_fastapi_ddd.shared.web.pagination import PageQuery


class ConfigCreateCommand(BaseModel):
    """创建配置命令。"""

    model_config = ConfigDict(extra="ignore")

    config_key: str
    config_value: str | None = None
    category: str | None = None
    remark: str | None = None
    sort_code: int = 0
    value_type: str = "STRING"
    label: str | None = None
    scope: str | None = None
    scene: str | None = None
    is_builtin: bool = False
    ext_json: dict[str, Any] = Field(default_factory=dict)


class ConfigUpdateCommand(ConfigCreateCommand):
    """更新配置命令。"""

    id: str


class ConfigAdminPageQuery(PageQuery):
    """配置后台分页。"""

    model_config = ConfigDict(extra="ignore")

    config_key: str | None = None
    category: str | None = None


class ConfigBatchItemCommand(BaseModel):
    """批量保存条目。"""

    model_config = ConfigDict(extra="ignore")

    config_key: str
    config_value: str | None = None
    category: str | None = None
    remark: str | None = None
    value_type: str | None = None
    label: str | None = None
    scope: str | None = None
    scene: str | None = None
    is_builtin: bool | None = None


class ConfigBatchSaveCommand(BaseModel):
    """批量保存命令。"""

    model_config = ConfigDict(extra="ignore")

    items: list[ConfigBatchItemCommand]


class CategoryQuery(BaseModel):
    """按分类查询。"""

    model_config = ConfigDict(extra="ignore")

    category: str | None = None
