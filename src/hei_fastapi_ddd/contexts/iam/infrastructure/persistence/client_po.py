""" Author: Charlie

客户端资源领域模型：客户端模块与客户端资源树节点。
"""

from sqlalchemy import JSON, Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin


class SysClientModule(Base, TimestampMixin):
    """客户端模块；account_type 区分账户体系（对齐 SysResourceModule.client）。"""

    __tablename__ = "sys_client_module"
    __table_args__ = (UniqueConstraint("code", name="uq_sys_client_module_code"),)

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="模块名称")
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="模块编码")
    account_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=AccountType.ADMIN.value,
        comment="账户体系",
    )
    icon: Mapped[str | None] = mapped_column(String(255), comment="图标")
    color: Mapped[str | None] = mapped_column(String(32), comment="颜色")
    sort: Mapped[int] = mapped_column(Integer, default=99, nullable=False, comment="排序")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=StatusEnum.ENABLED.value,
        comment="状态",
    )
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    extra: Mapped[dict] = mapped_column(JSON, default=dict, comment="扩展信息")


class SysClientResource(Base, TimestampMixin):
    """客户端资源树节点；归属 sys_client_module。"""

    __tablename__ = "sys_client_resource"
    __table_args__ = (
        UniqueConstraint("module_id", "code", name="uq_sys_client_resource_module_id_code"),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    parent_id: Mapped[str | None] = mapped_column(String(64), comment="父资源ID")
    code: Mapped[str] = mapped_column(String(64), nullable=False, comment="资源编码")
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="资源名称")
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="资源类型")
    module_id: Mapped[str | None] = mapped_column(String(64), comment="所属客户端模块ID")
    path: Mapped[str | None] = mapped_column(String(255), comment="路由路径")
    component: Mapped[str | None] = mapped_column(String(255), comment="前端组件")
    redirect: Mapped[str | None] = mapped_column(String(255), comment="重定向地址")
    icon: Mapped[str | None] = mapped_column(String(255), comment="图标")
    color: Mapped[str | None] = mapped_column(String(32), comment="颜色")
    href: Mapped[str | None] = mapped_column(String(255), comment="外链地址")
    sort: Mapped[int] = mapped_column(Integer, default=99, nullable=False, comment="排序")
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否可见")
    is_cache: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否缓存")
    is_affix: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否固定标签",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=StatusEnum.ENABLED.value,
        comment="状态",
    )
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    layout: Mapped[str | None] = mapped_column(String(255), comment="布局类型")
    extra: Mapped[dict] = mapped_column(JSON, default=dict, comment="扩展信息")
