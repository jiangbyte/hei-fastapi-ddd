""" Author: Charlie

消息数据模型：统一运营消息（SysNotice）与阅读记录（SysNoticeRead）。
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id


class SysNotice(Base, TimestampMixin):
    """统一运营消息（通知 / 公告）。"""

    __tablename__ = "sys_notice"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, nullable=False, default=generate_snowflake_id, comment="主键"
    )
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="类型：NOTIFICATION|ANNOUNCEMENT"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="内容")
    content_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="内容格式")
    category: Mapped[str | None] = mapped_column(String(32), comment="分类（通知）")
    severity: Mapped[str] = mapped_column(String(32), nullable=False, comment="等级")
    target_scope: Mapped[str] = mapped_column(String(32), nullable=False, comment="目标范围")
    target_account_types: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, comment="目标账户类型列表"
    )
    target_account_ids: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, comment="目标账户ID列表"
    )
    target_dept_ids: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, comment="目标部门ID列表"
    )
    target_role_ids: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, comment="目标角色ID列表"
    )
    publish_locations: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="发布位置（公告）"
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否置顶（公告）"
    )
    pinned_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="置顶截止时间"
    )
    sender_account_type: Mapped[str | None] = mapped_column(String(32), comment="发送者账户类型")
    sender_account_id: Mapped[str | None] = mapped_column(String(64), comment="发送者账户ID")
    source_type: Mapped[str | None] = mapped_column(String(64), comment="来源模块（通知）")
    source_id: Mapped[str | None] = mapped_column(String(64), comment="来源业务ID（通知）")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="状态")
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="发布时间")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="撤回时间")
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="过期时间（公告）")
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="查看次数")
    extra: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="扩展信息"
    )


class SysNoticeRead(Base):
    """消息阅读记录，对应 sys_notice_read 表。"""

    __tablename__ = "sys_notice_read"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, nullable=False, default=generate_snowflake_id, comment="主键"
    )
    notice_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="消息ID")
    account_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="账户类型")
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="账户ID")
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="阅读时间",
    )

    __table_args__ = (
        UniqueConstraint(
            "notice_id", "account_type", "account_id", name="uq_sys_notice_read_account"
        ),
    )
