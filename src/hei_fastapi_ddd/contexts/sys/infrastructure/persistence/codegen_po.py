""" Author: Charlie

代码生成方案模型（列名对齐 hei-boot sys_codegen_plan）。
"""
from sqlalchemy import Boolean, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin


class SysCodegenPlan(Base, TimestampMixin):
    """代码生成方案，描述单表、树表、左树右表和主子表的生成配置。"""

    __tablename__ = "sys_codegen_plan"
    __table_args__ = (
        UniqueConstraint("name", name="uq_sys_codegen_plan_name"),
        Index("ix_sys_codegen_plan_table_name", "table_name"),
        Index("ix_sys_codegen_plan_gen_type", "gen_type"),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="方案名称")
    gen_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="生成类型")
    author: Mapped[str] = mapped_column(String(64), nullable=False, comment="作者")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")

    table_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="主表名")
    pk_column: Mapped[str] = mapped_column(
        String(128), nullable=False, default="id", comment="主表主键"
    )
    entity_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="主实体类名")
    module_path: Mapped[str] = mapped_column(String(255), nullable=False, comment="后端模块路径")
    business_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="主业务名称")

    api_prefix: Mapped[str] = mapped_column(String(255), nullable=False, comment="接口前缀")
    permission_prefix: Mapped[str] = mapped_column(String(128), nullable=False, comment="权限前缀")
    resource_module_id: Mapped[str | None] = mapped_column(String(64), comment="资源模块ID")
    parent_resource_id: Mapped[str | None] = mapped_column(String(64), comment="父资源ID")
    menu_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="菜单名称")
    menu_path: Mapped[str] = mapped_column(String(255), nullable=False, comment="菜单路径")
    component_path: Mapped[str] = mapped_column(String(255), nullable=False, comment="组件路径")
    icon: Mapped[str | None] = mapped_column(String(255), comment="菜单图标")
    sort: Mapped[int] = mapped_column(Integer, default=99, nullable=False, comment="排序")

    tree_parent_field: Mapped[str | None] = mapped_column(String(128), comment="树父级字段")
    tree_label_field: Mapped[str | None] = mapped_column(String(128), comment="树展示字段")

    sub_table: Mapped[str | None] = mapped_column(String(128), comment="子表名")
    sub_pk: Mapped[str | None] = mapped_column(String(128), comment="子表主键")
    sub_foreign_key: Mapped[str | None] = mapped_column(String(128), comment="子表外键")
    sub_entity_name: Mapped[str | None] = mapped_column(String(128), comment="子实体类名")
    sub_business_name: Mapped[str | None] = mapped_column(String(128), comment="子业务名称")


class SysCodegenField(Base, TimestampMixin):
    """代码生成字段配置，保存数据库字段到模型、表格、表单和查询控件的映射。"""

    __tablename__ = "sys_codegen_field"
    __table_args__ = (
        UniqueConstraint(
            "plan_id", "table_role", "column_name", name="uq_sys_codegen_field_plan_role_column"
        ),
        Index("ix_sys_codegen_field_plan_role_sort", "plan_id", "table_role", "sort"),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="方案ID")
    table_role: Mapped[str] = mapped_column(
        String(16), nullable=False, default="MAIN", comment="表角色"
    )
    column_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="字段名")
    label: Mapped[str | None] = mapped_column(String(255), comment="字段注释")
    db_type: Mapped[str] = mapped_column(String(128), nullable=False, comment="数据库类型")
    value_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="str", comment="语义数据类型"
    )
    ui_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="string", comment="前端类型"
    )
    widget: Mapped[str] = mapped_column(
        String(32), nullable=False, default="input", comment="表单控件"
    )
    dict_code: Mapped[str | None] = mapped_column(String(128), comment="字典编码")
    query_operator: Mapped[str | None] = mapped_column(String(32), comment="查询方式")
    in_table: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="表格显示"
    )
    in_form: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="表单显示"
    )
    in_detail: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="详情显示"
    )
    in_query: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="查询显示"
    )
    primary_key: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否主键"
    )
    required: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否必填"
    )
    unique_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否唯一"
    )
    nullable: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否可空"
    )
    max_length: Mapped[int | None] = mapped_column(Integer, comment="最大长度")
    sort: Mapped[int] = mapped_column(Integer, default=99, nullable=False, comment="排序")
