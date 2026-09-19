""" Author: Charlie

弱密码库相关 Schema：创建/更新、分页与列表查询。
"""

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.web.pagination import PageQuery


class WeakPasswordCreateRequest(ApiSchema):
    """弱密码创建请求。"""

    password: str = Field(min_length=1, max_length=255)


class WeakPasswordUpdateRequest(WeakPasswordCreateRequest):
    """弱密码更新请求，在创建字段基础上增加主键。"""

    id: str = Field(min_length=1, max_length=64)


class WeakPasswordAdminPageQuery(PageQuery):
    """弱密码后台分页查询参数（keyword 为密码兜底过滤，对齐 hei-boot）。"""

    password: str | None = Field(default=None, max_length=255)
    keyword: str | None = Field(default=None, max_length=255)


class WeakPasswordListQuery(ApiSchema):
    """弱密码列表查询参数（keyword 为密码兜底过滤，对齐 hei-boot）。"""

    password: str | None = Field(default=None, max_length=255)
    keyword: str | None = Field(default=None, max_length=255)


class SysWeakPasswordSchema(ApiSchema):
    """弱密码响应模型。"""

    id: str
    password: str
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None
