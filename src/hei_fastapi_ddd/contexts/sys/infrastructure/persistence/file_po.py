""" Author: Charlie

文件元数据模型：记录对象存储路径、类型与访问地址等元信息。
"""

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.config.enums import StorageProvider
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin


class SysFile(Base, TimestampMixin):
    """文件元数据表，只记录对象存储信息，不使用数据库外键。"""

    __tablename__ = "sys_file"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    object_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="对象存储路径",
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    storage_provider: Mapped[StorageProvider] = mapped_column(
        String(32),
        nullable=False,
        comment="存储服务商：minio/rustfs/oss/s3",
    )
    bucket: Mapped[str | None] = mapped_column(String(255), comment="存储桶")
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, comment="文件类型")
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件大小")
    url: Mapped[str] = mapped_column(String(1024), nullable=False, comment="访问地址")
