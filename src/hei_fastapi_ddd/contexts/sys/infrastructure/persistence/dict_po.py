""" Author: Charlie

系统字典表模型，字段默认值与 sys_dict 字典条目的 value 保持一致。
"""
from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.config.enums import StatusEnum, SysBizCategory
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin


class SysDict(Base, TimestampMixin):
    """系统字典表，支持分类、选项值和父子树结构。"""

    __tablename__ = "sys_dict"
    __table_args__ = (
        Index("idx_sys_dict_code", "code", unique=True),
        Index("idx_sys_dict_category", "category"),
        Index("idx_sys_dict_parent_id", "parent_id"),
    )

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="编码")
    label: Mapped[str | None] = mapped_column(String(255), comment="标签")
    value: Mapped[str | None] = mapped_column(String(255), comment="值")
    color: Mapped[str | None] = mapped_column(String(32), comment="颜色")
    category: Mapped[str | None] = mapped_column(
        String(64),
        comment=f"系统/业务分类：{SysBizCategory.__doc__}",
    )
    parent_id: Mapped[str | None] = mapped_column(String(32), comment="父级ID")
    status: Mapped[str] = mapped_column(
        String(16),
        default=StatusEnum.ENABLED.value,
        nullable=False,
        comment="状态",
    )
    sort: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="排序",
    )
