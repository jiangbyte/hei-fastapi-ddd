""" Author: Charlie

由 HEI 代码生成器生成。
Author: jiangbyte

反馈数据模型：定义用户反馈记录（SysFeedback）对应的 sys_feedback 表结构。
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin


class SysFeedback(Base, TimestampMixin):
    """用户反馈记录，对应 sys_feedback 表。"""

    __tablename__ = "sys_feedback"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, nullable=False, default=generate_snowflake_id, comment="主键"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="反馈标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="反馈内容")
    category: Mapped[str] = mapped_column(String(64), nullable=False, comment="反馈分类")
    contact: Mapped[str | None] = mapped_column(String(255), comment="联系方式")
    attach_object_names: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, comment="附件 object_name 列表"
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="状态")
    reply: Mapped[str | None] = mapped_column(Text, comment="管理员回复")
    replied_by: Mapped[str | None] = mapped_column(String(64), comment="回复人ID")
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="回复时间")
    submitter_account_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="提交者账户类型"
    )
    submitter_account_id: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="提交者账户ID"
    )
