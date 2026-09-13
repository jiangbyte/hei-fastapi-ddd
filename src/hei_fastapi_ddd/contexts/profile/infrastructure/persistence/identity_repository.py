"""Author: Charlie

实名认证数据仓储。
"""

from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.contexts.profile.domain.identity.enums import RealNameBusinessType, RealNameCaseStatus
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_po import ProfileIdentity, RealNameCase, RealNameCaseRecord
from hei_fastapi_ddd.contexts.profile.interfaces.http.identity_schemas import (
    IdentityPageQuery,
    RealNameCaseMyPageQuery,
    RealNameCaseReviewPageQuery,
)


class ProfileIdentityRepository:
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

    async def page(self, query: IdentityPageQuery) -> tuple[list[ProfileIdentity], int]:
        stmt: Select[tuple[ProfileIdentity]] = select(ProfileIdentity)
        count_stmt = select(func.count(ProfileIdentity.account_id))
        filters = []
        if query.status:
            filters.append(ProfileIdentity.status == query.status)
        if query.account_id:
            filters.append(ProfileIdentity.account_id == query.account_id)
        if query.document_type:
            filters.append(ProfileIdentity.document_type == query.document_type)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(ProfileIdentity.verified_at.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total


class RealNameCaseRepository:
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

    async def page_my(
        self, query: RealNameCaseMyPageQuery, account_id: str
    ) -> tuple[list[RealNameCase], int]:
        stmt = select(RealNameCase).where(RealNameCase.account_id == account_id)
        count_stmt = select(func.count(RealNameCase.case_id)).where(
            RealNameCase.account_id == account_id
        )
        filters = []
        if query.business_type:
            filters.append(RealNameCase.business_type == query.business_type)
        if query.status:
            filters.append(RealNameCase.status == query.status)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(RealNameCase.created_at.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def page_review(
        self, query: RealNameCaseReviewPageQuery
    ) -> tuple[list[RealNameCase], int]:
        business_type = (
            query.business_type.strip()
            if query.business_type and query.business_type.strip()
            else RealNameBusinessType.ACCOUNT_VERIFY.value
        )
        stmt = select(RealNameCase).where(RealNameCase.business_type == business_type)
        count_stmt = select(func.count(RealNameCase.case_id)).where(
            RealNameCase.business_type == business_type
        )
        filters = []
        if query.status:
            filters.append(RealNameCase.status == query.status)
        if query.account_id:
            filters.append(RealNameCase.account_id == query.account_id)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(RealNameCase.created_at.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total


class RealNameCaseRecordRepository:
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
