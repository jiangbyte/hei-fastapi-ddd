"""Author: Charlie

实名认证业务服务（对齐 hei-boot ProfileIdentityService / RealNameCaseService）。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.exceptions.business import BusinessError, NotFoundError
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.storage.url import normalize_object_name
from hei_fastapi_ddd.contexts.profile.application.identity import crypto as identity_crypto
from hei_fastapi_ddd.contexts.profile.domain.identity.enums import (
    DOCUMENT_TYPES,
    IdentitySnapshotStatus,
    RealNameBusinessType,
    RealNameCaseStatus,
    VerifyChannel,
)
from hei_fastapi_ddd.contexts.profile.application.identity.handlers import RealNameBusinessHandlerRegistry
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_po import ProfileIdentity, RealNameCase
from hei_fastapi_ddd.contexts.profile.infrastructure.identity_providers.registry import get_provider_registry
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_repository import (
    ProfileIdentityRepository,
    RealNameCaseRecordRepository,
    RealNameCaseRepository,
)
from hei_fastapi_ddd.contexts.profile.interfaces.http.identity_schemas import (
    IdentityPageQuery,
    IdentityPageResponse,
    IdentityRevokeRequest,
    IdentityStatusResponse,
    RealNameBusinessOptionResponse,
    RealNameCaseApproveRequest,
    RealNameCaseAttachmentResponse,
    RealNameCaseCallbackRequest,
    RealNameCaseDetailResponse,
    RealNameCaseInitResponse,
    RealNameCaseInitThirdPartyRequest,
    RealNameCaseMyPageQuery,
    RealNameCaseOptionsResponse,
    RealNameCaseRejectRequest,
    RealNameCaseReviewPageQuery,
    RealNameCaseSubmitRequest,
    RealNameCaseSummaryResponse,
)
from hei_fastapi_ddd.contexts.profile.application.identity.support import sanitize_status, sanitize_summary
from hei_fastapi_ddd.contexts.sys.application.audit.support import resolve_account_login
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.file_repository import FileRepository
from hei_fastapi_ddd.contexts.sys.application.file.file_application_service import FileService


def _normalize_business_type(business_type: str | None) -> str:
    if not business_type or not business_type.strip():
        return RealNameBusinessType.ACCOUNT_VERIFY.value
    return business_type.strip().upper()


class ProfileIdentityService:
    """profile_identity 快照服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProfileIdentityRepository(db)
        self.case_repo = RealNameCaseRepository(db)

    async def get_status_for_account(self, account_id: str) -> IdentityStatusResponse:
        identity = await self.repo.get_by_account_id(account_id)
        result = IdentityStatusResponse(status=IdentitySnapshotStatus.UNVERIFIED.value)
        if identity is not None:
            result = IdentityStatusResponse(
                status=identity.status,
                document_type=identity.document_type,
                verify_channel=identity.verify_channel,
                provider=identity.provider,
                verified_at=identity.verified_at,
                revoked_at=identity.revoked_at,
            )
            if identity.real_name_cipher:
                result.real_name_masked = identity_crypto.mask_real_name(
                    identity_crypto.decrypt(identity.real_name_cipher)
                )
            if identity.document_no_cipher:
                result.document_no_masked = identity_crypto.mask_document_no(
                    identity_crypto.decrypt(identity.document_no_cipher)
                )

        pending = await self.case_repo.find_pending_by_account(account_id)
        if pending is not None:
            result.pending_case = _to_summary(pending)
        return result

    async def get_user_status_for_account(self, account_id: str) -> IdentityStatusResponse:
        return sanitize_status(await self.get_status_for_account(account_id))  # type: ignore[return-value]

    async def upsert_on_approve(self, case: RealNameCase, reviewer_id: str) -> None:
        identity = await self.repo.get_by_account_id(case.account_id or "")
        is_new = identity is None
        if identity is None:
            identity = ProfileIdentity(account_id=case.account_id or "")
            self.db.add(identity)
        else:
            audit_snapshots.before_entity(identity)
        identity.status = IdentitySnapshotStatus.VERIFIED.value
        identity.document_type = case.document_type
        identity.real_name_cipher = case.real_name_cipher
        identity.document_no_cipher = case.document_no_cipher
        identity.document_no_hash = case.document_no_hash
        identity.verify_channel = case.verify_channel
        identity.provider = case.provider
        identity.provider_order_no = case.provider_order_no
        identity.verified_at = datetime.now(UTC)
        identity.source_case_id = case.case_id
        identity.revoked_at = None
        identity.revoked_by = None
        await self.db.flush()
        if is_new:
            audit_snapshots.created_entity(identity)
        else:
            audit_snapshots.after_entity(identity)

    async def revoke(self, payload: IdentityRevokeRequest, operator_id: str) -> None:
        identity = await self.repo.get_by_account_id(payload.account_id)
        if identity is None or identity.status != IdentitySnapshotStatus.VERIFIED.value:
            raise NotFoundError("Verified identity not found")
        subject = await resolve_account_login(self.db, payload.account_id) or payload.account_id
        audit_snapshots.subject(subject)
        audit_snapshots.before_entity(identity)
        identity.status = IdentitySnapshotStatus.REVOKED.value
        identity.revoked_at = datetime.now(UTC)
        identity.revoked_by = operator_id
        await self.db.flush()
        audit_snapshots.after_entity(identity)

    async def page(self, query: IdentityPageQuery) -> PageData[IdentityPageResponse]:
        items, total = await self.repo.page(query)
        return build_page(query, total, [_to_page_result(item) for item in items])

    async def is_verified(self, account_id: str) -> bool:
        identity = await self.repo.get_by_account_id(account_id)
        return (
            identity is not None
            and identity.status == IdentitySnapshotStatus.VERIFIED.value
        )


class RealNameCaseService:
    """real_name_case 工单服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.case_repo = RealNameCaseRepository(db)
        self.record_repo = RealNameCaseRecordRepository(db)
        self.profile_service = ProfileIdentityService(db)
        self.handler_registry = RealNameBusinessHandlerRegistry(
            db, profile_service=self.profile_service
        )
        self.provider_registry = get_provider_registry()
        self.file_repo = FileRepository(db)
        self.file_service = FileService(db)

    async def options(self) -> RealNameCaseOptionsResponse:
        return RealNameCaseOptionsResponse(
            business_types=[
                RealNameBusinessOptionResponse(
                    business_type=RealNameBusinessType.ACCOUNT_VERIFY.value,
                    label="账号实名认证",
                    channels=[
                        VerifyChannel.MANUAL.value,
                        VerifyChannel.THIRD_PARTY.value,
                    ],
                )
            ],
            document_types=list(DOCUMENT_TYPES),
        )

    async def submit(self, payload: RealNameCaseSubmitRequest, session: SessionPayload) -> None:
        business_type = _normalize_business_type(payload.business_type)
        handler = self.handler_registry.require(business_type)
        await handler.validate_submit(session.account_id, payload)

        attachments = _normalize_attachment_ids(payload.attachment_ids)
        if not attachments:
            raise BusinessError("请上传证件材料")

        entity = RealNameCase(
            business_type=business_type,
            verify_channel=VerifyChannel.MANUAL.value,
            status=RealNameCaseStatus.PENDING.value,
            account_id=session.account_id,
            attachment_ids=attachments,
            submitter_id=session.account_id,
        )
        _fill_sensitive_fields(
            entity,
            payload.document_type,
            payload.real_name,
            payload.document_no,
        )
        if payload.applicant_contact and payload.applicant_contact.strip():
            entity.applicant_contact_cipher = identity_crypto.encrypt(
                payload.applicant_contact.strip()
            )

        async with transactional(self.db):
            await self.case_repo.create(entity)
            await self.record_repo.append(
                case=entity,
                action="SUBMIT",
                status_before=None,
                status_after=entity.status,
                operator_id=session.account_id,
            )
        audit_snapshots.created_entity(entity)

    async def init_third_party(
        self, payload: RealNameCaseInitThirdPartyRequest, session: SessionPayload
    ) -> RealNameCaseInitResponse:
        business_type = _normalize_business_type(payload.business_type)
        validate_param = RealNameCaseSubmitRequest(
            business_type=business_type,
            document_type=payload.document_type,
            real_name=payload.real_name,
            document_no=payload.document_no,
        )
        await self.handler_registry.require(business_type).validate_submit(
            session.account_id, validate_param
        )

        entity = RealNameCase(
            business_type=business_type,
            verify_channel=VerifyChannel.THIRD_PARTY.value,
            status=RealNameCaseStatus.PENDING.value,
            account_id=session.account_id,
            submitter_id=session.account_id,
        )
        _fill_sensitive_fields(
            entity,
            payload.document_type,
            payload.real_name,
            payload.document_no,
        )

        async with transactional(self.db):
            await self.case_repo.create(entity)
            provider = self.provider_registry.resolve(
                VerifyChannel.THIRD_PARTY.value,
                payload.document_type,
                payload.provider,
            )
            init_result = await provider.init_verify(entity, payload)
            entity.provider = init_result.provider
            entity.provider_order_no = init_result.provider_order_no
            await self.case_repo.update(entity)
            await self.record_repo.append(
                case=entity,
                action="INIT_THIRD_PARTY",
                status_before=None,
                status_after=entity.status,
                operator_id=session.account_id,
            )
            audit_snapshots.created_entity(entity)
            return init_result

    async def callback(self, payload: RealNameCaseCallbackRequest) -> None:
        entity = await self.case_repo.get_required(payload.case_id)
        if entity.status != RealNameCaseStatus.PENDING.value:
            raise BusinessError("Case is not pending")

        provider = self.provider_registry.resolve(
            entity.verify_channel,
            entity.document_type or "",
            entity.provider,
        )
        await provider.handle_callback(entity, payload)

        success = payload.success is True
        before = entity.status
        async with transactional(self.db):
            if success:
                entity.status = RealNameCaseStatus.APPROVED.value
                entity.reviewed_at = datetime.now(UTC)
                await self.case_repo.update(entity)
                await self.handler_registry.require(entity.business_type).on_approved(
                    entity, "SYSTEM"
                )
                await self.record_repo.append(
                    case=entity,
                    action="CALLBACK",
                    status_before=before,
                    status_after=entity.status,
                    operator_id="SYSTEM",
                    remark=payload.message,
                )
                audit_snapshots.after_entity(entity)
                return

            entity.status = RealNameCaseStatus.REJECTED.value
            entity.reviewed_at = datetime.now(UTC)
            entity.reject_reason = (
                payload.message.strip()
                if payload.message and payload.message.strip()
                else "Third-party verification failed"
            )
            await self.case_repo.update(entity)
            await self.handler_registry.require(entity.business_type).on_rejected(
                entity, "SYSTEM", entity.reject_reason
            )
            await self.record_repo.append(
                case=entity,
                action="CALLBACK",
                status_before=before,
                status_after=entity.status,
                operator_id="SYSTEM",
                remark=entity.reject_reason,
            )
            audit_snapshots.after_entity(entity)

    async def my_page(
        self, query: RealNameCaseMyPageQuery, session: SessionPayload
    ) -> PageData[RealNameCaseSummaryResponse]:
        items, total = await self.case_repo.page_my(query, session.account_id)
        summaries = [_to_summary(item) for item in items]
        sanitized = [sanitize_summary(item) for item in summaries]  # type: ignore[misc]
        return build_page(query, total, sanitized)

    async def review_page(
        self, query: RealNameCaseReviewPageQuery
    ) -> PageData[RealNameCaseSummaryResponse]:
        items, total = await self.case_repo.page_review(query)
        return build_page(query, total, [_to_summary(item) for item in items])

    async def detail(self, case_id: str) -> RealNameCaseDetailResponse:
        entity = await self.case_repo.get_required(case_id)
        result = RealNameCaseDetailResponse.model_validate(_to_summary(entity))
        result.provider = entity.provider
        result.provider_order_no = entity.provider_order_no
        result.submitter_id = entity.submitter_id
        result.reviewer_id = entity.reviewer_id
        result.attachments = await self._resolve_attachments(entity.attachment_ids or [])
        return result

    async def approve(
        self, payload: RealNameCaseApproveRequest, session: SessionPayload
    ) -> None:
        entity = await self.case_repo.get_required(payload.case_id)
        if entity.status != RealNameCaseStatus.PENDING.value:
            raise BusinessError("Case is not pending")
        subject = await resolve_account_login(self.db, entity.account_id or "") or (
            entity.account_id or ""
        )
        audit_snapshots.subject(subject)
        audit_snapshots.before_entity(entity)
        before = entity.status
        async with transactional(self.db):
            entity.status = RealNameCaseStatus.APPROVED.value
            entity.reviewer_id = session.account_id
            entity.reviewed_at = datetime.now(UTC)
            await self.case_repo.update(entity)
            await self.handler_registry.require(entity.business_type).on_approved(
                entity, session.account_id
            )
            await self.record_repo.append(
                case=entity,
                action="APPROVE",
                status_before=before,
                status_after=entity.status,
                operator_id=session.account_id,
                remark=payload.remark,
            )
        audit_snapshots.after_entity(entity)

    async def reject(
        self, payload: RealNameCaseRejectRequest, session: SessionPayload
    ) -> None:
        entity = await self.case_repo.get_required(payload.case_id)
        if entity.status != RealNameCaseStatus.PENDING.value:
            raise BusinessError("Case is not pending")
        subject = await resolve_account_login(self.db, entity.account_id or "") or (
            entity.account_id or ""
        )
        reject_reason = payload.reject_reason.strip()
        audit_snapshots.subject(subject)
        audit_snapshots.before_entity(entity)
        before = entity.status
        async with transactional(self.db):
            entity.status = RealNameCaseStatus.REJECTED.value
            entity.reviewer_id = session.account_id
            entity.reviewed_at = datetime.now(UTC)
            entity.reject_reason = reject_reason
            await self.case_repo.update(entity)
            await self.handler_registry.require(entity.business_type).on_rejected(
                entity, session.account_id, reject_reason
            )
            await self.record_repo.append(
                case=entity,
                action="REJECT",
                status_before=before,
                status_after=entity.status,
                operator_id=session.account_id,
                remark=reject_reason,
            )
        audit_snapshots.after_entity(entity)

    async def _resolve_attachments(
        self, attachment_ids: list[str]
    ) -> list[RealNameCaseAttachmentResponse]:
        if not attachment_ids:
            return []
        files = await self.file_repo.list_by_object_names(attachment_ids)
        url_map = await self.file_service.resolve_access_urls(attachment_ids)
        attachments: list[RealNameCaseAttachmentResponse] = []
        for file in files:
            object_name = file.object_name
            resolved_url = url_map.get(object_name) or url_map.get(file.object_name)
            attachments.append(
                RealNameCaseAttachmentResponse(
                    object_name=object_name,
                    id=file.id,
                    original_name=file.original_name,
                    content_type=file.content_type,
                    size=file.size,
                    url=resolved_url or file.url,
                )
            )
        return attachments


def _fill_sensitive_fields(
    entity: RealNameCase,
    document_type: str | None,
    real_name: str | None,
    document_no: str | None,
) -> None:
    entity.document_type = (
        document_type.strip().upper() if document_type and document_type.strip() else None
    )
    entity.real_name_cipher = identity_crypto.encrypt(real_name)
    entity.document_no_cipher = identity_crypto.encrypt(document_no)
    entity.document_no_hash = identity_crypto.hash_document_no(
        entity.document_type, document_no
    )


def _normalize_attachment_ids(attachment_ids: list[str] | None) -> list[str]:
    if not attachment_ids:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in attachment_ids:
        if not item or not str(item).strip():
            continue
        value = normalize_object_name(str(item).strip())
        if value and value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized


def _to_summary(entity: RealNameCase) -> RealNameCaseSummaryResponse:
    summary = RealNameCaseSummaryResponse(
        case_id=entity.case_id,
        account_id=entity.account_id,
        business_type=entity.business_type,
        verify_channel=entity.verify_channel,
        status=entity.status,
        document_type=entity.document_type,
        created_at=entity.created_at,
        reviewed_at=entity.reviewed_at,
        reject_reason=entity.reject_reason,
    )
    if entity.real_name_cipher:
        summary.real_name_masked = identity_crypto.mask_real_name(
            identity_crypto.decrypt(entity.real_name_cipher)
        )
    if entity.document_no_cipher:
        summary.document_no_masked = identity_crypto.mask_document_no(
            identity_crypto.decrypt(entity.document_no_cipher)
        )
    return summary


def _to_page_result(identity: ProfileIdentity) -> IdentityPageResponse:
    result = IdentityPageResponse(
        account_id=identity.account_id,
        status=identity.status,
        document_type=identity.document_type,
        verify_channel=identity.verify_channel,
        provider=identity.provider,
        verified_at=identity.verified_at,
        revoked_at=identity.revoked_at,
    )
    if identity.real_name_cipher:
        result.real_name_masked = identity_crypto.mask_real_name(
            identity_crypto.decrypt(identity.real_name_cipher)
        )
    if identity.document_no_cipher:
        result.document_no_masked = identity_crypto.mask_document_no(
            identity_crypto.decrypt(identity.document_no_cipher)
        )
    return result
