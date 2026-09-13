""" Author: Charlie

账户组领域模型：账户组表，作为批量授权与分组管理的载体。
"""

from sqlalchemy import JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.config.enums import StatusEnum
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin


class SysGroup(Base, TimestampMixin):
    """账户组表，作为批量授权、批量分组和批量例外授权的载体。"""

    __tablename__ = "sys_group"
    __table_args__ = (UniqueConstraint("name", name="uq_sys_group_name"),)

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_snowflake_id, comment="主键"
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="账户组名称")
    owner_dept_id: Mapped[str | None] = mapped_column(String(64), comment="所属部门ID")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=StatusEnum.ENABLED.value,
        comment="状态",
    )
    extra: Mapped[dict] = mapped_column(JSON, default=dict, comment="扩展信息")
