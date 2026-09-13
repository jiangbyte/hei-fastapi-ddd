"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:53
"""

from typing import Any

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import OwnerDeptMixin, TimestampMixin


class CgTestCatalog(Base, TimestampMixin, OwnerDeptMixin):
    __tablename__ = "cg_test_catalog"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, default=generate_snowflake_id, comment="主键")
    parent_id: Mapped[str | None] = mapped_column(String(64), comment="父级ID")
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="目录编码")
    name: Mapped[str] = mapped_column(String(120), nullable=False, comment="目录名称")
    category: Mapped[str | None] = mapped_column(String(32), comment="目录分类")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="状态")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, comment="排序")
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否显示")
    icon: Mapped[str | None] = mapped_column(String(128), comment="图标")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="扩展信息")
