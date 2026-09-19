"""cg_test_order 应用层 DTO。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CgTestOrderCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_no: str
    name: str
    customer_name: str
    customer_phone: str | None = None
    status: str
    type: str
    ordered_at: datetime
    paid_at: datetime | None = None
    total_amount: float
    item_count: int
    need_invoice: bool
    invoice_config: dict[str, Any]
    remark: str | None = None
    extra: dict[str, Any] | None = Field(default_factory=dict)


class CgTestOrderUpdateCommand(CgTestOrderCreateCommand):
    id: str


class CgTestOrderPageQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current: int = 1
    size: int = 20
    order_no: str | None = None
    name: str | None = None
    customer_name: str | None = None
    status: str | None = None
    type: str | None = None

    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size


class CgTestOrderItemCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order_id: str
    sku_code: str
    name: str
    category: str | None = None
    status: str
    quantity: int
    unit_price: float
    shipped_at: datetime | None = None
    is_gift: bool
    item_config: dict[str, Any]
    remark: str | None = None
    extra: dict[str, Any] | None = Field(default_factory=dict)


class CgTestOrderItemUpdateCommand(CgTestOrderItemCreateCommand):
    id: str


class CgTestOrderItemPageQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current: int = 1
    size: int = 20
    order_id: str | None = None
    name: str | None = None
    sku_code: str | None = None
    status: str | None = None

    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size
