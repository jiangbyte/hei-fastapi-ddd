""" Author: Charlie

部门 Schema：部门创建/更新/分页查询及树节点结构。
"""

from datetime import datetime

from pydantic import Field, field_serializer

from hei_fastapi_ddd.shared.config.enums import StatusEnum
from hei_fastapi_ddd.shared.web.pagination import PageQuery
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt


class DeptCreateRequest(ApiSchema):
    """创建部门请求。"""

    name: str
    category: str
    parent_id: str | None = None
    master_id: str | None = None
    deputy_master_id: str | None = None
    sort: WireInt = 99
    is_virtual: WireBool = False
    status: StatusEnum = StatusEnum.ENABLED
    extra: dict = Field(default_factory=dict)


class DeptUpdateRequest(DeptCreateRequest):
    """更新部门请求。"""

    id: str = Field(min_length=1, max_length=64)


class DeptAdminPageQuery(PageQuery):
    """部门管理端分页查询条件。"""

    name: str | None = Field(default=None, max_length=64)
    category: str | None = Field(default=None, max_length=64)
    parent_id: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=32)


class SysDeptSchema(ApiSchema):
    """部门响应结构，含负责人与父级名称回显。"""

    id: str
    parent_id: str | None = None
    parent_name: str | None = None
    master_id: str | None = None
    master_name: str | None = None
    deputy_master_id: str | None = None
    deputy_master_name: str | None = None
    name: str
    category: str
    sort: WireInt
    is_virtual: WireBool
    status: str
    extra: dict
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None
    children: list["SysDeptSchema"] = Field(default_factory=list)
    children: list["SysDeptSchema"] = Field(default_factory=list)


class DeptTreeNode(ApiSchema):
    """部门树节点结构（对齐 hei-boot TreeUtil + trans）。"""

    id: str
    name: str
    category: str
    parent_id: str | None = None
    master_id: str | None = None
    master_name: str | None = None
    deputy_master_id: str | None = None
    deputy_master_name: str | None = None
    status: str
    sort: WireInt = 99
    weight: WireInt = 99
    is_virtual: WireBool = False
    extra: dict = Field(default_factory=dict)
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime | None = None
    updated_by: str | None = None
    children: list["DeptTreeNode"] | None = Field(default=None)

    @field_serializer("children", when_used="json")
    def _omit_empty_children(self, value: list["DeptTreeNode"] | None):
        """空列表序列化为 None，使叶子节点省略 children 键。"""
        return value or None
