""" Author: Charlie

密码变更历史 — 记录密码 hash 以防复用，
并驱动密码到期提醒（等保）。

每账户最新一条作为 canonical ``password_updated_at`` 时间戳；
无历史记录的账户回退到账户行的 ``updated_at``（来自 TimestampMixin）。
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id


class SysAccountPasswordHistory(Base):
    """密码变更历史记录。"""

    __tablename__ = "sys_account_password_history"
    __table_args__ = (Index("idx_pwd_history_account_created", "account_id", "created_at"),)

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="账户ID")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    changed_by: Mapped[str | None] = mapped_column(String(64), comment="变更人（账户ID或系统）")
    change_reason: Mapped[str | None] = mapped_column(
        String(64), comment="变更原因: register / admin_reset / self_reset / password_expired"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="变更时间",
    )
