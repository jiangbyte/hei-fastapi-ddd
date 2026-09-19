"""Author: Charlie

实名工单 PO 构建辅助（仅基础设施层使用）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hei_fastapi_ddd.contexts.profile.application.identity import crypto as identity_crypto
from hei_fastapi_ddd.contexts.profile.domain.identity.enums import RealNameCaseStatus, VerifyChannel
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_po import RealNameCase


def fill_sensitive_fields(entity: RealNameCase, document_type: str, real_name: str, document_no: str) -> None:
    entity.document_type = document_type
    entity.real_name_cipher = identity_crypto.encrypt(real_name.strip())
    entity.document_no_cipher = identity_crypto.encrypt(document_no.strip())
    entity.document_no_hash = identity_crypto.hash_document_no(document_type, document_no)


def build_manual_case(
    *,
    account_id: str,
    business_type: str,
    payload: Mapping[str, Any],
    attachments: list[str],
) -> RealNameCase:
    entity = RealNameCase(
        business_type=business_type,
        verify_channel=VerifyChannel.MANUAL.value,
        status=RealNameCaseStatus.PENDING.value,
        account_id=account_id,
        attachment_ids=attachments,
        submitter_id=account_id,
    )
    fill_sensitive_fields(
        entity,
        str(payload["document_type"]),
        str(payload["real_name"]),
        str(payload["document_no"]),
    )
    contact = payload.get("applicant_contact")
    if contact and str(contact).strip():
        entity.applicant_contact_cipher = identity_crypto.encrypt(str(contact).strip())
    return entity


def build_third_party_case(
    *,
    account_id: str,
    business_type: str,
    payload: Mapping[str, Any],
) -> RealNameCase:
    entity = RealNameCase(
        business_type=business_type,
        verify_channel=VerifyChannel.THIRD_PARTY.value,
        status=RealNameCaseStatus.PENDING.value,
        account_id=account_id,
        submitter_id=account_id,
    )
    fill_sensitive_fields(
        entity,
        str(payload["document_type"]),
        str(payload["real_name"]),
        str(payload["document_no"]),
    )
    return entity
