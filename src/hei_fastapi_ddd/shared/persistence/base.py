""" Author: Charlie

ORM 基类与元数据：声明统一的 SQLAlchemy 命名约定，并在末尾挂载审计字段注入钩子。

所有模型通过继承 Base 获得一致的约束/索引命名，便于迁移与排查。
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# 统一约束/索引命名约定，避免自动生成名称不一致。
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""

    metadata = metadata


# 在 Session.flush 时注册 TimestampMixin created_by / updated_by 注入。
from hei_fastapi_ddd.shared.persistence import audit as _audit_hooks  # noqa: E402, F401
