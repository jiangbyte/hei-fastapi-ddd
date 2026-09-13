""" Author: Charlie

IAM 通用关系领域模型：sys_iam_relation 统一承载成员关系、资源权限挂载与主体授权规则。
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.config.enums import DataScope, StatusEnum
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.contexts.iam.domain.enums import (
    GrantMode,
    IamRelationSubjectType,
    IamRelationTargetType,
)


class SysIamRelation(Base, TimestampMixin):
    """IAM 通用关系表，统一承载成员关系、资源权限挂载和主体授权规则。"""

    __tablename__ = "sys_iam_relation"
    __table_args__ = (
        UniqueConstraint(
            "subject_type",
            "subject_id",
            "relation_type",
            "target_type",
            "target_id",
            "target_key",
            "account_type",
            name="uq_sys_iam_relation_subject_relation_target",
        ),
        Index("ix_sys_iam_relation_subject", "subject_type", "subject_id", "relation_type"),
        Index("ix_sys_iam_relation_target", "target_type", "target_id", "target_key"),
        Index("ix_sys_iam_relation_account_type_relation", "account_type", "relation_type"),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="主体类型")
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="主体ID")
    account_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="账户类型")
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="关系类型")
    target_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="目标类型")
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", comment="目标ID")
    target_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="",
        comment="目标标识",
    )
    grant_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=GrantMode.CASCADE.value,
        comment="授权模式",
    )
    data_scope: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DataScope.SELF.value,
        comment="数据范围",
    )
    custom_scope_dept_ids: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        comment="自定义数据范围部门ID列表",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="主关系",
    )
    sort: Mapped[int] = mapped_column(Integer, default=99, nullable=False, comment="排序")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=StatusEnum.ENABLED.value,
        comment="状态",
    )
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    reason: Mapped[str | None] = mapped_column(Text, comment="授权原因")
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="失效时间")
    extra: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, comment="扩展信息")

    @property
    def account_id(self) -> str | None:
        """从主体或目标侧提取账户 ID（无账户参与时返回 None）。"""
        if self.subject_type == IamRelationSubjectType.ACCOUNT.value:
            return self.subject_id
        if self.target_type == IamRelationTargetType.ACCOUNT.value:
            return self.target_id
        return None

    @property
    def group_id(self) -> str | None:
        """从主体或目标侧提取账户组 ID。"""
        if self.subject_type == IamRelationSubjectType.GROUP.value:
            return self.subject_id
        if self.target_type == IamRelationTargetType.GROUP.value:
            return self.target_id
        return None

    @property
    def role_id(self) -> str | None:
        """从主体或目标侧提取角色 ID。"""
        if self.subject_type == IamRelationSubjectType.ROLE.value:
            return self.subject_id
        if self.target_type == IamRelationTargetType.ROLE.value:
            return self.target_id
        return None

    @property
    def dept_id(self) -> str | None:
        """当目标为部门时返回部门 ID。"""
        if self.target_type == IamRelationTargetType.DEPT.value:
            return self.target_id
        return None

    @property
    def resource_id(self) -> str | None:
        """从主体或目标侧提取资源 ID。"""
        if self.subject_type == IamRelationSubjectType.RESOURCE.value:
            return self.subject_id
        if self.target_type == IamRelationTargetType.RESOURCE.value:
            return self.target_id
        return None

    @property
    def permission_key(self) -> str | None:
        """当目标为权限时返回权限码。"""
        if self.target_type == IamRelationTargetType.PERMISSION.value:
            return self.target_key
        return None
