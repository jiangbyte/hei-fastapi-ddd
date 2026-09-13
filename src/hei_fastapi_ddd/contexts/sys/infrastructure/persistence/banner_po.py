""" Author: Charlie

展示图内容表模型，字段默认值与 sys_dict 字典条目的 value 保持一致。
"""
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.config.enums import StatusEnum
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.contexts.sys.domain.banner.enums import (
    BannerCategory,
    BannerLinkType,
    BannerPosition,
    BannerType,
)


class SysBanner(Base, TimestampMixin):
    """展示图内容表，面向管理端和公开端的展示位统一建模。"""

    __tablename__ = "sys_banner"
    __table_args__ = (
        Index(
            "ix_sys_banner_position_status_sort",
            "position",
            "status",
            "sort",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="标题")
    image: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="图片 object_name（读取时由服务层解析为 URL）"
    )
    url: Mapped[str | None] = mapped_column(String(500), comment="跳转地址")
    link_type: Mapped[str] = mapped_column(
        String(16),
        default=BannerLinkType.URL.value,
        nullable=False,
        comment=f"链接类型：{BannerLinkType.__doc__}",
    )
    summary: Mapped[str | None] = mapped_column(String(500), comment="摘要")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment=f"分类：{BannerCategory.__doc__}",
    )
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment=f"类型：{BannerType.__doc__}",
    )
    position: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment=f"显示位置：{BannerPosition.__doc__}",
    )
    target_account_types: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="目标账户类型列表（AccountType：ADMIN/PORTAL）",
    )
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")
    interaction_count: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="交互次数",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=StatusEnum.ENABLED.value,
        nullable=False,
        comment="状态",
    )
    start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        comment="开始展示时间",
    )
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        comment="结束展示时间",
    )
