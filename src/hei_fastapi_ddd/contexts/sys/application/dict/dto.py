"""字典应用层 DTO（非 HTTP 契约）。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from hei_fastapi_ddd.shared.web.pagination import PageQuery


class DictCreateCommand(BaseModel):
    """创建字典命令。"""

    model_config = ConfigDict(extra="ignore")

    code: str
    label: str | None = None
    value: str | None = None
    color: str | None = None
    category: str | None = None
    parent_id: str | None = None
    status: str = "ENABLED"
    sort: int = 0


class DictUpdateCommand(DictCreateCommand):
    """更新字典命令。"""

    id: str


class DictIdQuery(BaseModel):
    """字典主键查询。"""

    model_config = ConfigDict(extra="ignore")

    id: str


class DictIdsCommand(BaseModel):
    """批量删除字典。"""

    model_config = ConfigDict(extra="ignore")

    ids: list[str] = Field(min_length=1)


class DictAdminPageQuery(PageQuery):
    """字典后台分页查询。"""

    model_config = ConfigDict(extra="ignore")

    code: str | None = None
    category: str | None = None
    parent_id: str | None = None
    status: str | None = None


class DictTreeQuery(BaseModel):
    """字典树查询。"""

    model_config = ConfigDict(extra="ignore")

    category: str | None = None
