"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:52
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import OwnerDeptMixin, TimestampMixin


class CgTestActivity(Base, TimestampMixin, OwnerDeptMixin):
    __tablename__ = "cg_test_activity"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, default=generate_snowflake_id, comment="主键")
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="活动编码")
    name: Mapped[str] = mapped_column(String(120), nullable=False, comment="活动名称")
    category: Mapped[str | None] = mapped_column(String(32), comment="活动分类")
    type: Mapped[str] = mapped_column(String(32), nullable=False, comment="活动类型")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="状态")
    cover_url: Mapped[str | None] = mapped_column(String(512), comment="封面地址")
    description: Mapped[str | None] = mapped_column(Text, comment="活动描述")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="开始时间")
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="结束时间")
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False, comment="最大参与人数")
    price: Mapped[float] = mapped_column(Numeric, nullable=False, comment="报名费用")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否公开")
    need_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否需要审批")
    rule_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="规则配置")
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="扩展信息")
