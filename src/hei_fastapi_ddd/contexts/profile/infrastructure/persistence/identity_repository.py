"""Author: Charlie

实名认证数据仓储。
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_case_support import (
    build_manual_case,
    build_third_party_case,
)
from hei_fastapi_ddd.contexts.profile.application.identity import crypto as identity_crypto
from hei_fastapi_ddd.contexts.profile.domain.identity.enums import (
    IdentitySnapshotStatus,
    RealNameBusinessType,
    RealNameCaseStatus,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_po import (
    ProfileIdentity,
    RealNameCase,
    RealNameCaseRecord,
)
from hei_fastapi_ddd.types.business import NotFoundError


class ProfileIdentityRepositoryImpl:
    """profile_identity 表仓储。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_account_id(self, account_id: str) -> ProfileIdentity | None:
        return await self.db.get(ProfileIdentity, account_id)

    async def get_required(self, account_id: str) -> ProfileIdentity:
        entity = await self.get_by_account_id(account_id)
        if entity is None:
            raise NotFoundError("Verified identity not found")
        return entity

    async def find_verified_by_document_hash(
        self, document_hash: str, *, exclude_account_id: str | None = None
    ) -> ProfileIdentity | None:
        stmt = select(ProfileIdentity).where(
            ProfileIdentity.document_no_hash == document_hash,
            ProfileIdentity.status == "VERIFIED",
        )
        if exclude_account_id:
            stmt = stmt.where(ProfileIdentity.account_id != exclude_account_id)
        return (await self.db.execute(stmt.limit(1))).scalar_one_or_none()

    async def page(
        self, filters: Mapping[str, Any], *, offset: int, limit: int
    ) -> tuple[list[ProfileIdentity], int]:
        stmt: Select[tuple[ProfileIdentity]] = select(ProfileIdentity)
        count_stmt = select(func.count(ProfileIdentity.account_id))
        where = []
        if filters.get("status"):
            where.append(ProfileIdentity.status == filters["status"])
        if filters.get("account_id"):
            where.append(ProfileIdentity.account_id == filters["account_id"])
        if filters.get("document_type"):
            where.append(ProfileIdentity.document_type == filters["document_type"])
        if where:
            stmt = stmt.where(*where)
            count_stmt = count_stmt.where(*where)
        stmt = stmt.order_by(ProfileIdentity.verified_at.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def upsert_verified_from_case(self, case: RealNameCase, reviewer_id: str) -> None:
        identity = await self.get_by_account_id(case.account_id or "")
        is_new = identity is None
        if identity is None:
            identity = ProfileIdentity(account_id=case.account_id or "")
            self.db.add(identity)
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
        return None if not is_new else None

    async def revoke_identity(self, account_id: str, operator_id: str) -> ProfileIdentity:
        identity = await self.get_required(account_id)
        identity.status = IdentitySnapshotStatus.REVOKED.value
        identity.revoked_at = datetime.now(UTC)
        identity.revoked_by = operator_id
        await self.db.flush()
        return identity


ProfileIdentityRepository = ProfileIdentityRepositoryImpl


class RealNameCaseRepositoryImpl:
    """real_name_case 表仓储。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, case_id: str) -> RealNameCase | None:
        return await self.db.get(RealNameCase, case_id)

    async def get_required(self, case_id: str) -> RealNameCase:
        entity = await self.get_by_id(case_id)
        if entity is None:
            raise NotFoundError("Real-name case not found")
        return entity

    async def create(self, entity: RealNameCase) -> RealNameCase:
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def update(self, entity: RealNameCase) -> RealNameCase:
        await self.db.flush()
        return entity

    async def count_pending_by_account(
        self, account_id: str, business_type: str
    ) -> int:
        stmt = select(func.count(RealNameCase.case_id)).where(
            RealNameCase.account_id == account_id,
            RealNameCase.business_type == business_type,
            RealNameCase.status == RealNameCaseStatus.PENDING.value,
        )
        return int((await self.db.execute(stmt)).scalar_one())

    async def find_pending_by_account(self, account_id: str) -> RealNameCase | None:
        stmt = (
            select(RealNameCase)
            .where(
                RealNameCase.account_id == account_id,
                RealNameCase.status == RealNameCaseStatus.PENDING.value,
            )
            .order_by(RealNameCase.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_pending_by_document_hash(
        self, document_hash: str, *, exclude_account_id: str | None = None
    ) -> RealNameCase | None:
        stmt = select(RealNameCase).where(
            RealNameCase.document_no_hash == document_hash,
            RealNameCase.status == RealNameCaseStatus.PENDING.value,
        )
        if exclude_account_id:
            stmt = stmt.where(RealNameCase.account_id != exclude_account_id)
        return (await self.db.execute(stmt.limit(1))).scalar_one_or_none()

    async def create_manual_submission(
        self,
        *,
        account_id: str,
        business_type: str,
        payload: Mapping[str, Any],
        attachments: list[str],
    ) -> RealNameCase:
        entity = build_manual_case(
            account_id=account_id,
            business_type=business_type,
            payload=payload,
            attachments=attachments,
        )
        return await self.create(entity)

    async def create_third_party_draft(
        self,
        *,
        account_id: str,
        business_type: str,
        payload: Mapping[str, Any],
    ) -> RealNameCase:
        entity = build_third_party_case(
            account_id=account_id,
            business_type=business_type,
            payload=payload,
        )
        return await self.create(entity)

    async def page_my(
        self,
        filters: Mapping[str, Any],
        account_id: str,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[RealNameCase], int]:
        stmt = select(RealNameCase).where(RealNameCase.account_id == account_id)
        count_stmt = select(func.count(RealNameCase.case_id)).where(
            RealNameCase.account_id == account_id
        )
        where = []
        if filters.get("business_type"):
            where.append(RealNameCase.business_type == filters["business_type"])
        if filters.get("status"):
            where.append(RealNameCase.status == filters["status"])
        if where:
            stmt = stmt.where(*where)
            count_stmt = count_stmt.where(*where)
        stmt = stmt.order_by(RealNameCase.created_at.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def page_review(
        self, filters: Mapping[str, Any], *, offset: int, limit: int
    ) -> tuple[list[RealNameCase], int]:
        business_type = (
            str(filters.get("business_type") or "").strip()
            or RealNameBusinessType.ACCOUNT_VERIFY.value
        )
        stmt = select(RealNameCase).where(RealNameCase.business_type == business_type)
        count_stmt = select(func.count(RealNameCase.case_id)).where(
            RealNameCase.business_type == business_type
        )
        where = []
        if filters.get("status"):
            where.append(RealNameCase.status == filters["status"])
        if filters.get("account_id"):
            where.append(RealNameCase.account_id == filters["account_id"])
        if where:
            stmt = stmt.where(*where)
            count_stmt = count_stmt.where(*where)
        stmt = stmt.order_by(RealNameCase.created_at.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total


RealNameCaseRepository = RealNameCaseRepositoryImpl


class RealNameCaseRecordRepositoryImpl:
    """real_name_case_record 表仓储。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def append(
        self,
        *,
        case: RealNameCase,
        action: str,
        status_before: str | None,
        status_after: str | None,
        operator_id: str | None,
        remark: str | None = None,
    ) -> RealNameCaseRecord:
        record = RealNameCaseRecord(
            case_id=case.case_id,
            account_id=case.account_id,
            business_type=case.business_type,
            action=action,
            status_before=status_before,
            status_after=status_after,
            verify_channel=case.verify_channel,
            provider=case.provider,
            operator_id=operator_id,
            remark=remark,
            created_at=datetime.now(UTC),
        )
        self.db.add(record)
        await self.db.flush()
        return record


RealNameCaseRecordRepository = RealNameCaseRecordRepositoryImpl
