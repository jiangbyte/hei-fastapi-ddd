""" Author: Charlie

门户账户资料数据模型：定义扩展资料表 profile_user_portal。
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin


class ProfileUserPortal(Base, TimestampMixin):
    """门户账户扩展资料表，承接展示资料和联系方式。"""

    __tablename__ = "profile_user_portal"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="账户ID")
    nickname: Mapped[str | None] = mapped_column(String(64), comment="昵称")
    avatar: Mapped[str | None] = mapped_column(Text, comment="头像")
    signature: Mapped[str | None] = mapped_column(Text, comment="个性签名")
    phone: Mapped[str | None] = mapped_column(String(32), comment="手机号")
    email: Mapped[str | None] = mapped_column(String(128), comment="邮箱")
