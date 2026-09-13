""" Author: Charlie

告警历史 — 记录已分发告警以供冷却去重。
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id


class SysAlertLog(Base):
    """告警发送记录。"""

    __tablename__ = "sys_alert_log"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_snowflake_id, comment="主键"
    )
    rule_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="规则名称")
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="严重级别: INFO/WARNING/CRITICAL"
    )
    summary: Mapped[str] = mapped_column(String(255), nullable=False, comment="告警摘要")
    details: Mapped[dict | None] = mapped_column(JSON, comment="告警详情（JSON）")
    notified_via: Mapped[str | None] = mapped_column(String(64), comment="通知方式: email/webhook")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="通知时间",
    )
