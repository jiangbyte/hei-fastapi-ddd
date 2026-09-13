""" Author: Charlie

弱密码库表模型 — 供密码策略查询。
"""
from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id


class SysWeakPassword(Base, TimestampMixin):
    """弱密码库，存储禁止使用的明文密码值。"""

    __tablename__ = "sys_weak_password"
    __table_args__ = (Index("idx_sys_weak_password_password", "password", unique=True),)

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="弱密码值")
