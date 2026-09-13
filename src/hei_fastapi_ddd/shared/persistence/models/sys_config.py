""" Author: Charlie

系统配置表模型 — 供框架基础设施查询。
"""
from sqlalchemy import JSON, Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin


class SysConfig(Base, TimestampMixin):
    """系统配置表，维护后台可配置键值数据。"""

    __tablename__ = "sys_config"
    __table_args__ = (
        Index("idx_sys_config_key", "config_key", unique=True),
        Index("idx_sys_config_category", "category"),
        Index("idx_sys_config_category_scope_scene", "category", "scope", "scene"),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    config_key: Mapped[str] = mapped_column(String(255), nullable=False, comment="配置键")
    config_value: Mapped[str | None] = mapped_column(Text, comment="配置值")
    category: Mapped[str | None] = mapped_column(String(255), comment="分类")
    remark: Mapped[str | None] = mapped_column(String(255), comment="备注")
    sort_code: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序码")
    value_type: Mapped[str] = mapped_column(
        String(32),
        default="STRING",
        nullable=False,
        comment="值类型: STRING|JSON|BOOL|NUMBER",
    )
    label: Mapped[str | None] = mapped_column(String(128), comment="展示名")
    scope: Mapped[str | None] = mapped_column(String(32), comment="作用域账户类型")
    scene: Mapped[str | None] = mapped_column(String(64), comment="场景编码")
    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否内置（不可删除）",
    )
    ext_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, comment="扩展信息")
