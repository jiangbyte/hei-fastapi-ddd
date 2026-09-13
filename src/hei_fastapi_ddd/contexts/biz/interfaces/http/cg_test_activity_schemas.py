"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:52
"""

from datetime import datetime
from typing import Any

from pydantic import Field

from hei_fastapi_ddd.shared.schema.base import ApiSchema, Id
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt, WireMoney
from hei_fastapi_ddd.shared.web.pagination import PageQuery


class CgTestActivityCreateRequest(ApiSchema):
    code: str
    name: str
    category: str | None = None
    type: str
    status: str
    cover_url: str | None = None
    description: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    max_participants: WireInt
    price: WireMoney
    is_public: WireBool
    need_approval: WireBool
    rule_config: dict[str, Any]
    extra: dict[str, Any] | None = Field(default_factory=dict)


class CgTestActivityUpdateRequest(CgTestActivityCreateRequest):
    id: Id


class CgTestActivityAdminPageQuery(PageQuery):
    code: str | None = None
    name: str | None = None
    category: str | None = None
    type: str | None = None
    status: str | None = None


class CgTestActivitySchema(ApiSchema):
    id: str
    code: str
    name: str
    category: str | None = None
    type: str
    status: str
    cover_url: str | None = None
    description: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    max_participants: WireInt
    price: WireMoney
    is_public: WireBool
    need_approval: WireBool
    rule_config: dict[str, Any]
    extra: dict[str, Any] | None = Field(default_factory=dict)
    created_at: datetime
    created_by: str | None = None
    owner_dept_id: str | None = None
    updated_at: datetime
    updated_by: str | None = None