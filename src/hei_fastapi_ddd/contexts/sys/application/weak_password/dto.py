"""弱密码库应用层 DTO。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from hei_fastapi_ddd.shared.web.pagination import PageQuery


class WeakPasswordCreateCommand(BaseModel):
    """创建弱密码命令。"""

    model_config = ConfigDict(extra="ignore")

    password: str


class WeakPasswordUpdateCommand(WeakPasswordCreateCommand):
    """更新弱密码命令。"""

    id: str


class WeakPasswordAdminPageQuery(PageQuery):
    """弱密码后台分页查询。"""

    model_config = ConfigDict(extra="ignore")

    password: str | None = None
    keyword: str | None = None


class WeakPasswordListQuery(BaseModel):
    """弱密码列表查询。"""

    model_config = ConfigDict(extra="ignore")

    password: str | None = None
    keyword: str | None = None


class WeakPasswordIdsCommand(BaseModel):
    """批量删除。"""

    model_config = ConfigDict(extra="ignore")

    ids: list[str] = Field(min_length=1)
