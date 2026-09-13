""" Author: Charlie

操作审计日志模型：记录每次敏感操作的前后数据与请求上下文（对齐 hei-boot）。
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id


class SysOperationAuditLog(Base):
    """操作审计日志表：持久化 IAM 与资源操作的审计轨迹。"""

    __tablename__ = "sys_operation_audit_log"
    __table_args__ = (
        Index("idx_sys_operation_audit_created_at", "created_at"),
        Index("idx_sys_operation_audit_account_id", "account_id"),
        Index("idx_sys_operation_audit_module_action", "module", "action"),
        Index(
            "idx_sys_operation_audit_resource",
            "resource_type",
            "resource_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    module: Mapped[str] = mapped_column(String(64), nullable=False, comment="模块")
    resource_type: Mapped[str | None] = mapped_column(String(128), comment="资源类型")
    resource_id: Mapped[str | None] = mapped_column(String(128), comment="资源ID")
    action: Mapped[str] = mapped_column(String(64), nullable=False, comment="操作")
    summary: Mapped[str | None] = mapped_column(String(2000), comment="摘要")
    before_data: Mapped[dict | None] = mapped_column(JSON, comment="变更前数据")
    after_data: Mapped[dict | None] = mapped_column(JSON, comment="变更后数据")
    account_id: Mapped[str | None] = mapped_column(String(64), comment="操作账号ID")
    account_type: Mapped[str | None] = mapped_column(String(32), comment="操作账号类型")
    request_id: Mapped[str | None] = mapped_column(String(64), comment="请求ID")
    ip: Mapped[str | None] = mapped_column(String(64), comment="客户端IP")
    user_agent: Mapped[str | None] = mapped_column(String(512), comment="User-Agent")
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否成功")
    error_message: Mapped[str | None] = mapped_column(Text, comment="错误信息")
    operator_name: Mapped[str | None] = mapped_column(String(128), comment="操作人昵称快照")
    action_name: Mapped[str | None] = mapped_column(String(128), comment="操作名")
    action_type: Mapped[str | None] = mapped_column(String(32), comment="操作类型")
    module_label: Mapped[str | None] = mapped_column(String(128), comment="操作模块展示名")
    duration_ms: Mapped[int | None] = mapped_column(Integer, comment="执行时长（毫秒）")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
