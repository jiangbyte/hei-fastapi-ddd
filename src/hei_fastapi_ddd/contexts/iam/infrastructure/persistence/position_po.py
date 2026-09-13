""" Author: Charlie

职位领域模型：职位表，用于描述岗位体系，本身不直接承载授权关系。
"""

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.config.enums import StatusEnum
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin


class SysPosition(Base, TimestampMixin):
    """职位表，用于描述岗位体系，本身不直接承担授权关系。"""

    __tablename__ = "sys_position"
    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_snowflake_id, comment="主键"
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="职位名称")
    category: Mapped[str] = mapped_column(String(32), nullable=False, comment="职位类别")
    owner_dept_id: Mapped[str | None] = mapped_column(String(64), comment="所属部门ID")
    sort: Mapped[int] = mapped_column(Integer, default=99, nullable=False, comment="排序")
    is_virtual: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否虚拟职位"
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=StatusEnum.ENABLED.value,
        comment="状态",
    )
    description: Mapped[str | None] = mapped_column(Text, comment="职位描述")
    extra: Mapped[dict] = mapped_column(JSON, default=dict, comment="扩展信息")
