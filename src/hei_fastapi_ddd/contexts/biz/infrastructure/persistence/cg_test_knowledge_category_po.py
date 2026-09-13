"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:55
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import OwnerDeptMixin, TimestampMixin
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id


class CgTestKnowledgeCategory(Base, TimestampMixin, OwnerDeptMixin):
    __tablename__ = "cg_test_knowledge_category"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, default=generate_snowflake_id, comment="主键")
    parent_id: Mapped[str | None] = mapped_column(String(64), comment="父级ID")
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="分类编码")
    name: Mapped[str] = mapped_column(String(120), nullable=False, comment="分类名称")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="状态")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, comment="排序")
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否显示")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="扩展信息")


class CgTestKnowledgeDoc(Base, TimestampMixin):
    __tablename__ = "cg_test_knowledge_doc"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, default=generate_snowflake_id, comment="主键")
    category_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="分类ID")
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="文档编码")
    title: Mapped[str] = mapped_column(String(160), nullable=False, comment="文档标题")
    type: Mapped[str] = mapped_column(String(32), nullable=False, comment="文档类型")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="状态")
    summary: Mapped[str | None] = mapped_column(String(512), comment="摘要")
    content: Mapped[str | None] = mapped_column(Text, comment="正文内容")
    author: Mapped[str | None] = mapped_column(String(64), comment="作者")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="发布时间")
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="浏览次数")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, comment="排序")
    is_top: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否置顶")
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="展示设置")
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="扩展信息")
