"""Author: Charlie

实名认证 ORM 模型：profile_identity、real_name_case、real_name_case_record。
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin
from hei_fastapi_ddd.shared.persistence.types import JsonTextList


class ProfileIdentity(Base, TimestampMixin):
    """账号实名认证快照。"""

    __tablename__ = "profile_identity"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="账号 ID")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="UNVERIFIED", comment="快照状态"
    )
    document_type: Mapped[str | None] = mapped_column(String(32), comment="证件类型")
    real_name_cipher: Mapped[str | None] = mapped_column(Text, comment="姓名密文")
    document_no_cipher: Mapped[str | None] = mapped_column(Text, comment="证件号密文")
    document_no_hash: Mapped[str | None] = mapped_column(String(128), comment="证件号哈希")
    verify_channel: Mapped[str | None] = mapped_column(String(32), comment="认证通道")
    provider: Mapped[str | None] = mapped_column(String(32), comment="第三方 Provider")
    provider_order_no: Mapped[str | None] = mapped_column(String(128), comment="第三方订单号")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="认证时间")
    source_case_id: Mapped[str | None] = mapped_column(String(64), comment="来源工单 ID")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="撤销时间")
    revoked_by: Mapped[str | None] = mapped_column(String(64), comment="撤销人")


class RealNameCase(Base, TimestampMixin):
    """实名业务工单。"""

    __tablename__ = "real_name_case"

    case_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_snowflake_id, comment="工单 ID"
    )
    business_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="业务类型")
    verify_channel: Mapped[str] = mapped_column(String(32), nullable=False, comment="认证通道")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="工单状态")
    account_id: Mapped[str | None] = mapped_column(String(64), comment="账号 ID")
    target_account_hint_cipher: Mapped[str | None] = mapped_column(Text, comment="目标账号提示密文")
    applicant_contact_cipher: Mapped[str | None] = mapped_column(Text, comment="申请人联系方式密文")
    document_type: Mapped[str | None] = mapped_column(String(32), comment="证件类型")
    real_name_cipher: Mapped[str | None] = mapped_column(Text, comment="姓名密文")
    document_no_cipher: Mapped[str | None] = mapped_column(Text, comment="证件号密文")
    document_no_hash: Mapped[str | None] = mapped_column(String(128), comment="证件号哈希")
    attachment_ids: Mapped[list[str]] = mapped_column(
        JsonTextList, nullable=False, default=list, comment="附件 object_name 列表"
    )
    payload_cipher: Mapped[str | None] = mapped_column(Text, comment="扩展载荷密文")
    handler_dept_id: Mapped[str | None] = mapped_column(String(64), comment="处理部门 ID")
    provider: Mapped[str | None] = mapped_column(String(32), comment="第三方 Provider")
    provider_order_no: Mapped[str | None] = mapped_column(String(128), comment="第三方订单号")
    submitter_id: Mapped[str | None] = mapped_column(String(64), comment="提交人 ID")
    reviewer_id: Mapped[str | None] = mapped_column(String(64), comment="审核人 ID")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="审核时间")
    reject_reason: Mapped[str | None] = mapped_column(String(512), comment="驳回原因")
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="过期时间")


class RealNameCaseRecord(Base):
    """实名业务工单流水。"""

    __tablename__ = "real_name_case_record"

    record_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_snowflake_id, comment="流水 ID"
    )
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="工单 ID")
    account_id: Mapped[str | None] = mapped_column(String(64), comment="账号 ID")
    business_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="业务类型")
    action: Mapped[str] = mapped_column(String(32), nullable=False, comment="动作")
    status_before: Mapped[str | None] = mapped_column(String(32), comment="变更前状态")
    status_after: Mapped[str | None] = mapped_column(String(32), comment="变更后状态")
    verify_channel: Mapped[str | None] = mapped_column(String(32), comment="认证通道")
    provider: Mapped[str | None] = mapped_column(String(32), comment="第三方 Provider")
    operator_id: Mapped[str | None] = mapped_column(String(64), comment="操作人 ID")
    dept_id: Mapped[str | None] = mapped_column(String(64), comment="部门 ID")
    remark: Mapped[str | None] = mapped_column(String(512), comment="备注")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="创建时间"
    )
