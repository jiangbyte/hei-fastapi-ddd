"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:54
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import OwnerDeptMixin, TimestampMixin


class CgTestOrder(Base, TimestampMixin, OwnerDeptMixin):
    __tablename__ = "cg_test_order"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, default=generate_snowflake_id, comment="主键")
    order_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="订单号")
    name: Mapped[str] = mapped_column(String(120), nullable=False, comment="订单名称")
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False, comment="客户名称")
    customer_phone: Mapped[str | None] = mapped_column(String(32), comment="客户手机号")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="状态")
    type: Mapped[str] = mapped_column(String(32), nullable=False, comment="订单类型")
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="下单时间")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="支付时间")
    total_amount: Mapped[float] = mapped_column(Numeric, nullable=False, comment="订单金额")
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="商品数量")
    need_invoice: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否开票")
    invoice_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="发票配置")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="扩展信息")


class CgTestOrderItem(Base, TimestampMixin):
    __tablename__ = "cg_test_order_item"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, default=generate_snowflake_id, comment="主键")
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="订单ID")
    sku_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="SKU编码")
    name: Mapped[str] = mapped_column(String(120), nullable=False, comment="商品名称")
    category: Mapped[str | None] = mapped_column(String(32), comment="商品分类")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="状态")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, comment="数量")
    unit_price: Mapped[float] = mapped_column(Numeric, nullable=False, comment="单价")
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="发货时间")
    is_gift: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否赠品")
    item_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="明细配置")
    remark: Mapped[str | None] = mapped_column(Text, comment="备注")
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="扩展信息")
