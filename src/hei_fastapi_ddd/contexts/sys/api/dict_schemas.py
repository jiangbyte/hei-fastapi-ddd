""" Author: Charlie

系统字典模块 Schema，类型字段使用枚举以保证值和字典数据一致。
"""
from datetime import datetime
from typing import Annotated

from pydantic import Field, field_serializer

from hei_fastapi_ddd.shared.config.enums import StatusEnum, SysBizCategory
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireInt
from hei_fastapi_ddd.shared.web.pagination import PageQuery

DictId = Annotated[str, Field(min_length=1, max_length=32)]  # 字典主键类型，长度 1-32


class DictCreateRequest(ApiSchema):
    """字典创建请求。"""

    code: str = Field(min_length=1, max_length=50, pattern=r"^[A-Z0-9_]+$")
    label: str | None = Field(default=None, max_length=255)
    value: str | None = Field(default=None, max_length=255)
    color: str | None = Field(default=None, max_length=32)
    category: SysBizCategory | None = None
    parent_id: DictId | None = None
    status: StatusEnum = StatusEnum.ENABLED
    sort: WireInt = 0


class DictUpdateRequest(DictCreateRequest):
    """字典更新请求，在创建字段基础上增加主键。"""

    id: DictId


class DictIdQuery(ApiSchema):
    """字典主键查询参数。"""

    id: DictId


class DictIdsRequest(ApiSchema):
    """字典批量删除请求。"""

    ids: list[DictId] = Field(min_length=1)


class DictAdminPageQuery(PageQuery):
    """字典后台分页查询参数（code 模糊匹配、category 自由字符串，对齐 hei-boot）。"""

    code: str | None = Field(default=None, max_length=50)
    category: str | None = Field(default=None, max_length=32)
    parent_id: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=16)


class DictTreeQuery(ApiSchema):
    """字典树查询参数（category 自由字符串，对齐 hei-boot）。"""

    category: str | None = Field(default=None, max_length=32)


class SysDictSchema(ApiSchema):
    """字典响应模型，含父级名称与创建/更新人昵称。"""

    id: str
    code: str
    label: str | None = None
    value: str | None = None
    color: str | None = None
    category: SysBizCategory | None = None
    parent_id: str | None = None
    parent_id_name: str | None = None
    status: StatusEnum | str
    sort: WireInt
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None
    children: list["SysDictTreeNode"] = Field(default_factory=list)


class SysDictTreeNode(ApiSchema):
    """字典树节点响应模型（name/weight 对齐 hei-boot 树线格式）。"""

    id: str
    code: str
    label: str | None = None
    name: str | None = None
    value: str | None = None
    color: str | None = None
    category: SysBizCategory | None = None
    parent_id: str | None = None
    parent_id_name: str | None = None
    status: StatusEnum | str
    sort: WireInt
    weight: WireInt = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    children: list["SysDictTreeNode"] = Field(default_factory=list)

    @field_serializer("children", when_used="json")
    def serialize_children(self, children: list["SysDictTreeNode"]) -> list | None:
        """空 children 不出现在 JSON（对齐 hei-boot Hutool Tree）。"""
        return children if children else None
