""" Author: Charlie

工作台个人快捷应用模型（对齐 hei-boot sys_workspace_shortcut）。
"""

from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin


class SysWorkspaceShortcut(Base, TimestampMixin):
    """工作台个人快捷应用。"""

    __tablename__ = "sys_workspace_shortcut"
    __table_args__ = (
        UniqueConstraint("account_id", "resource_id", name="uq_sys_workspace_shortcut_account_resource"),
        Index("ix_sys_workspace_shortcut_account_sort", "account_id", "sort"),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="账号ID")
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="菜单资源ID")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, comment="排序")
