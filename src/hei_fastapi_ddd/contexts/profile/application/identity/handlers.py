"""Author: Charlie

实名业务 Handler：按 business_type 路由（对齐 hei-boot）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from hei_fastapi_ddd.contexts.profile.application.identity.identity_application_service import (
        ProfileIdentityService,
    )

from hei_fastapi_ddd.contexts.profile.application.identity import crypto as identity_crypto
from hei_fastapi_ddd.contexts.profile.domain.identity.enums import (
    IdentitySnapshotStatus,
    RealNameBusinessType,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_po import RealNameCase
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_repository import (
    ProfileIdentityRepository,
    RealNameCaseRepository,
)
from hei_fastapi_ddd.contexts.profile.interfaces.http.identity_schemas import (
    RealNameCaseSubmitRequest,
)
from hei_fastapi_ddd.shared.exceptions.business import BusinessError


class RealNameBusinessHandler(Protocol):
    def business_type(self) -> str: ...

    async def validate_submit(
        self, account_id: str, param: RealNameCaseSubmitRequest
    ) -> None: ...

    async def on_approved(self, case: RealNameCase, reviewer_id: str) -> None: ...

    async def on_rejected(
        self, case: RealNameCase, reviewer_id: str, reason: str
    ) -> None: ...


class AccountVerifyHandler:
    """账号实名认证业务 Handler。"""

    def __init__(self, db: AsyncSession, profile_service: ProfileIdentityService | None = None):
        self.db = db
        self.identity_repo = ProfileIdentityRepository(db)
        self.case_repo = RealNameCaseRepository(db)
        self._profile_service = profile_service

    def business_type(self) -> str:
        return RealNameBusinessType.ACCOUNT_VERIFY.value

    async def validate_submit(self, account_id: str, param: RealNameCaseSubmitRequest) -> None:
        identity = await self.identity_repo.get_by_account_id(account_id)
        if identity is not None and identity.status == IdentitySnapshotStatus.VERIFIED.value:
            raise BusinessError("账号已完成实名认证")
        pending = await self.case_repo.count_pending_by_account(account_id, self.business_type())
        if pending > 0:
            raise BusinessError("已有进行中的实名认证申请")
        await self.assert_document_available(
            param.document_type, param.document_no, exclude_account_id=account_id
        )

    async def on_approved(self, case: RealNameCase, reviewer_id: str) -> None:
        if self._profile_service is None:
            from hei_fastapi_ddd.contexts.profile.application.identity.identity_application_service import (
                ProfileIdentityService,
            )

            self._profile_service = ProfileIdentityService(self.db)
        await self._profile_service.upsert_on_approve(case, reviewer_id)

    async def on_rejected(
        self, case: RealNameCase, reviewer_id: str, reason: str
    ) -> None:
        return None

    async def assert_document_available(
        self,
        document_type: str | None,
        document_no: str | None,
        *,
        exclude_account_id: str | None = None,
    ) -> None:
        if not document_no or not str(document_no).strip():
            raise BusinessError("证件号码不能为空")
        document_hash = identity_crypto.hash_document_no(document_type, document_no)
        if not document_hash:
            raise BusinessError("证件号码不能为空")
        bound = await self.identity_repo.find_verified_by_document_hash(
            document_hash, exclude_account_id=exclude_account_id
        )
        if bound is not None:
            raise BusinessError("该证件已被其他账号绑定")
        pending_case = await self.case_repo.find_pending_by_document_hash(
            document_hash, exclude_account_id=exclude_account_id
        )
        if pending_case is not None:
            raise BusinessError("该证件已有进行中的认证申请")


class RealNameBusinessHandlerRegistry:
    def __init__(self, db: AsyncSession, profile_service: ProfileIdentityService | None = None):
        handlers: list[RealNameBusinessHandler] = [
            AccountVerifyHandler(db, profile_service=profile_service),
        ]
        self._handlers = {handler.business_type().upper(): handler for handler in handlers}

    def require(self, business_type: str) -> RealNameBusinessHandler:
        if not business_type or not business_type.strip():
            raise BusinessError("business_type is required")
        handler = self._handlers.get(business_type.strip().upper())
        if handler is None:
            raise BusinessError(f"Unsupported business_type: {business_type}")
        return handler
