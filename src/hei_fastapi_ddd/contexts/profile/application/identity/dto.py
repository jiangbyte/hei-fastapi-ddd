"""Author: Charlie

实名认证 API schema（snake_case JSON，对齐 hei-boot param/result DTO）。
"""

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.shared.schema.base import ApiSchema, Id
from hei_fastapi_ddd.shared.web.pagination import PageQuery

# ---------- 请求参数 ----------


class RealNameCaseSubmitCommand(ApiSchema):
    business_type: str | None = None
    document_type: str
    real_name: str
    document_no: str
    attachment_ids: list[str] = Field(default_factory=list)
    applicant_contact: str | None = None


class RealNameCaseInitThirdPartyCommand(ApiSchema):
    business_type: str | None = None
    document_type: str
    real_name: str
    document_no: str
    provider: str | None = None


class RealNameCaseCallbackCommand(ApiSchema):
    case_id: str
    provider_order_no: str | None = None
    success: bool | None = None
    message: str | None = None


class RealNameCaseApproveCommand(ApiSchema):
    case_id: str
    remark: str | None = None


class RealNameCaseRejectCommand(ApiSchema):
    case_id: str
    reject_reason: str


class IdentityRevokeCommand(ApiSchema):
    account_id: str
    remark: str | None = None


class RealNameCaseMyPageQuery(PageQuery):
    business_type: str | None = None
    status: str | None = None


class RealNameCaseReviewPageQuery(PageQuery):
    business_type: str | None = None
    status: str | None = None
    account_id: str | None = None


class IdentityPageQuery(PageQuery):
    status: str | None = None
    account_id: str | None = None
    document_type: str | None = None


# ---------- 响应结果 ----------


class RealNameBusinessOptionResponse(ApiSchema):
    business_type: str
    label: str
    channels: list[str] = Field(default_factory=list)


class RealNameCaseOptionsResponse(ApiSchema):
    business_types: list[RealNameBusinessOptionResponse] = Field(default_factory=list)
    document_types: list[str] = Field(default_factory=list)


class RealNameCaseInitResponse(ApiSchema):
    case_id: str
    provider: str
    provider_order_no: str
    redirect_url: str | None = None


class RealNameCaseSummaryResponse(ApiSchema):
    case_id: str
    account_id: str | None = None
    business_type: str
    verify_channel: str | None = None
    status: str
    document_type: str | None = None
    real_name_masked: str | None = None
    document_no_masked: str | None = None
    created_at: datetime | None = None
    reviewed_at: datetime | None = None
    reject_reason: str | None = None


class RealNameCaseAttachmentResponse(ApiSchema):
    object_name: str
    id: Id | None = None
    original_name: str | None = None
    content_type: str | None = None
    size: int | None = None
    url: str | None = None


class RealNameCaseDetailResponse(RealNameCaseSummaryResponse):
    provider: str | None = None
    provider_order_no: str | None = None
    submitter_id: str | None = None
    reviewer_id: str | None = None
    attachments: list[RealNameCaseAttachmentResponse] = Field(default_factory=list)


class IdentityStatusResponse(ApiSchema):
    status: str
    document_type: str | None = None
    real_name_masked: str | None = None
    document_no_masked: str | None = None
    verify_channel: str | None = None
    provider: str | None = None
    verified_at: datetime | None = None
    revoked_at: datetime | None = None
    pending_case: RealNameCaseSummaryResponse | None = None


class IdentityPageResponse(ApiSchema):
    account_id: str
    status: str
    document_type: str | None = None
    real_name_masked: str | None = None
    document_no_masked: str | None = None
    verify_channel: str | None = None
    provider: str | None = None
    verified_at: datetime | None = None
    revoked_at: datetime | None = None
