"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:54
"""

from datetime import datetime
from typing import Any

from pydantic import Field

from hei_fastapi_ddd.shared.web.pagination import PageQuery
from hei_fastapi_ddd.shared.schema.base import ApiSchema, Id
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt, WireMoney


class CgTestOrderCreateRequest(ApiSchema):
    order_no: str
    name: str
    customer_name: str
    customer_phone: str | None = None
    status: str
    type: str
    ordered_at: datetime
    paid_at: datetime | None = None
    total_amount: WireMoney
    item_count: WireInt
    need_invoice: WireBool
    invoice_config: dict[str, Any]
    remark: str | None = None
    extra: dict[str, Any] | None = Field(default_factory=dict)


class CgTestOrderUpdateRequest(CgTestOrderCreateRequest):
    id: Id


class CgTestOrderAdminPageQuery(PageQuery):
    order_no: str | None = None
    name: str | None = None
    customer_name: str | None = None
    status: str | None = None
    type: str | None = None


class CgTestOrderSchema(ApiSchema):
    id: str
    order_no: str
    name: str
    customer_name: str
    customer_phone: str | None = None
    status: str
    type: str
    ordered_at: datetime
    paid_at: datetime | None = None
    total_amount: WireMoney
    item_count: WireInt
    need_invoice: WireBool
    invoice_config: dict[str, Any]
    remark: str | None = None
    extra: dict[str, Any] | None = Field(default_factory=dict)
    created_at: datetime
    created_by: str | None = None
    owner_dept_id: str | None = None
    updated_at: datetime
    updated_by: str | None = None

class CgTestOrderItemCreateRequest(ApiSchema):
    order_id: str
    sku_code: str
    name: str
    category: str | None = None
    status: str
    quantity: WireInt
    unit_price: WireMoney
    shipped_at: datetime | None = None
    is_gift: WireBool
    item_config: dict[str, Any]
    remark: str | None = None
    extra: dict[str, Any] | None = Field(default_factory=dict)


class CgTestOrderItemUpdateRequest(CgTestOrderItemCreateRequest):
    id: Id


class CgTestOrderItemAdminPageQuery(PageQuery):
    order_id: str | None = Field(default=None, max_length=64)
    sku_code: str | None = None
    name: str | None = None
    status: str | None = None


class CgTestOrderItemSchema(ApiSchema):
    id: str
    order_id: str
    sku_code: str
    name: str
    category: str | None = None
    status: str
    quantity: WireInt
    unit_price: WireMoney
    shipped_at: datetime | None = None
    is_gift: WireBool
    item_config: dict[str, Any]
    remark: str | None = None
    extra: dict[str, Any] | None = Field(default_factory=dict)
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None