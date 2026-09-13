"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:55
"""

from datetime import datetime
from typing import Any

from pydantic import Field, field_serializer

from hei_fastapi_ddd.shared.schema.base import ApiSchema, Id
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt
from hei_fastapi_ddd.shared.web.pagination import PageQuery


class CgTestKnowledgeCategoryCreateRequest(ApiSchema):
    parent_id: str | None = None
    code: str
    name: str
    status: str
    sort: WireInt
    is_visible: WireBool
    description: str | None = None
    extra: dict[str, Any]


class CgTestKnowledgeCategoryUpdateRequest(CgTestKnowledgeCategoryCreateRequest):
    id: Id


class CgTestKnowledgeCategoryAdminPageQuery(PageQuery):
    code: str | None = None
    name: str | None = None
    status: str | None = None


class CgTestKnowledgeCategorySchema(ApiSchema):
    id: str
    parent_id: str | None = None
    code: str
    name: str
    status: str
    sort: WireInt
    is_visible: WireBool
    description: str | None = None
    extra: dict[str, Any]
    created_at: datetime
    created_by: str | None = None
    owner_dept_id: str | None = None
    updated_at: datetime
    updated_by: str | None = None
    children: list["CgTestKnowledgeCategoryTreeNode"] = Field(default_factory=list)


class CgTestKnowledgeCategoryDetailSchema(CgTestKnowledgeCategorySchema):
    parent_id_name: str | None = None


class CgTestKnowledgeCategoryTreeNode(CgTestKnowledgeCategorySchema):
    """树节点（对齐 hei-boot TreeUtil：weight + 叶子省略 children）。"""

    weight: WireInt | None = None
    children: list["CgTestKnowledgeCategoryTreeNode"] | None = Field(default=None)

    @field_serializer("children", when_used="json")
    def _omit_empty_children(self, value: list["CgTestKnowledgeCategoryTreeNode"] | None):
        return value or None


class CgTestKnowledgeDocCreateRequest(ApiSchema):
    category_id: str
    code: str
    title: str
    type: str
    status: str
    summary: str | None = None
    content: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    view_count: WireInt
    sort: WireInt
    is_top: WireBool
    settings: dict[str, Any]
    extra: dict[str, Any] | None = Field(default_factory=dict)


class CgTestKnowledgeDocUpdateRequest(CgTestKnowledgeDocCreateRequest):
    id: Id


class CgTestKnowledgeDocAdminPageQuery(PageQuery):
    category_id: str | None = Field(default=None, max_length=64)
    code: str | None = None
    title: str | None = None
    type: str | None = None
    status: str | None = None


class CgTestKnowledgeDocSchema(ApiSchema):
    id: str
    category_id: str
    code: str
    title: str
    type: str
    status: str
    summary: str | None = None
    content: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    view_count: WireInt
    sort: WireInt
    is_top: WireBool
    settings: dict[str, Any]
    extra: dict[str, Any] | None = Field(default_factory=dict)
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None