""" Author: Charlie

部门领域模型：部门表，承载组织归属、层级关系与部门管理元信息。
"""

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.config.enums import StatusEnum
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id


class SysDept(Base, TimestampMixin):
    """部门表，只承担组织归属、层级关系和部门管理元信息。"""

    __tablename__ = "sys_dept"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_snowflake_id, comment="主键"
    )
    parent_id: Mapped[str | None] = mapped_column(String(64), comment="父部门ID")
    master_id: Mapped[str | None] = mapped_column(String(64), comment="主管ID")
    deputy_master_id: Mapped[str | None] = mapped_column(String(64), comment="副主管ID")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="部门名称")
    category: Mapped[str] = mapped_column(String(64), nullable=False, comment="部门类别")
    sort: Mapped[int] = mapped_column(Integer, default=99, nullable=False, comment="排序")
    is_virtual: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否虚拟部门"
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=StatusEnum.ENABLED.value,
        comment="状态",
    )
    extra: Mapped[dict] = mapped_column(JSON, default=dict, comment="扩展信息")
