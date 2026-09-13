""" Author: Charlie

三方登录绑定表模型（对齐 hei-boot sys_account_oauth_binding）。
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id


class SysAccountOauthBinding(Base, TimestampMixin):
    """账号三方登录绑定快照，provider+open_id 全局唯一，account_id+provider 唯一。"""

    __tablename__ = "sys_account_oauth_binding"
    __table_args__ = (
        UniqueConstraint("provider", "open_id", name="uq_oauth_provider_open_id"),
        UniqueConstraint("account_id", "provider", name="uq_oauth_account_provider"),
        Index("idx_oauth_binding_account", "account_id"),
        Index("idx_oauth_binding_union", "union_id"),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="账户ID")
    provider: Mapped[str] = mapped_column(String(32), nullable=False, comment="提供商")
    open_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="平台 openid")
    union_id: Mapped[str | None] = mapped_column(String(128), comment="微信 unionid")
    nickname: Mapped[str | None] = mapped_column(String(128), comment="平台昵称")
    avatar: Mapped[str | None] = mapped_column(Text, comment="平台头像")
    raw_profile: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="平台原始资料 JSON",
    )
    bound_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="绑定时间",
    )
