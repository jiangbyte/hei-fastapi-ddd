"""Author: Charlie

实名认证仓储与 Provider 端口（应用层依赖）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class ProfileIdentityRepositoryPort(Protocol):
    async def get_by_account_id(self, account_id: str) -> Any | None:
        ...

    async def get_required(self, account_id: str) -> Any:
        ...

    async def find_verified_by_document_hash(
        self, document_hash: str, *, exclude_account_id: str | None = None
    ) -> Any | None:
        ...

    async def page(
        self, filters: Mapping[str, Any], *, offset: int, limit: int
    ) -> tuple[list[Any], int]:
        ...

    async def upsert_verified_from_case(self, case: Any, reviewer_id: str) -> None:
        ...

    async def revoke_identity(self, account_id: str, operator_id: str) -> Any:
        ...


class RealNameCaseRepositoryPort(Protocol):
    async def get_by_id(self, case_id: str) -> Any | None:
        ...

    async def get_required(self, case_id: str) -> Any:
        ...

    async def create(self, entity: Any) -> Any:
        ...

    async def update(self, entity: Any) -> Any:
        ...

    async def create_manual_submission(
        self,
        *,
        account_id: str,
        business_type: str,
        payload: Mapping[str, Any],
        attachments: list[str],
    ) -> Any:
        ...

    async def create_third_party_draft(
        self,
        *,
        account_id: str,
        business_type: str,
        payload: Mapping[str, Any],
    ) -> Any:
        ...

    async def count_pending_by_account(self, account_id: str, business_type: str) -> int:
        ...

    async def find_pending_by_account(self, account_id: str) -> Any | None:
        ...

    async def find_pending_by_document_hash(
        self, document_hash: str, *, exclude_account_id: str | None = None
    ) -> Any | None:
        ...

    async def page_my(
        self, filters: Mapping[str, Any], account_id: str, *, offset: int, limit: int
    ) -> tuple[list[Any], int]:
        ...

    async def page_review(
        self, filters: Mapping[str, Any], *, offset: int, limit: int
    ) -> tuple[list[Any], int]:
        ...


class RealNameCaseRecordRepositoryPort(Protocol):
    async def append(
        self,
        *,
        case: Any,
        action: str,
        status_before: str | None,
        status_after: str | None,
        operator_id: str | None,
        remark: str | None = None,
    ) -> Any:
        ...


class IdentityVerifyProviderPort(Protocol):
    def provider_code(self) -> str:
        ...

    def supports(self, verify_channel: str, document_type: str) -> bool:
        ...

    async def init_verify(self, case: Any, param: Any) -> Any:
        ...

    async def handle_callback(self, case: Any, param: Any) -> None:
        ...


class IdentityVerifyProviderRegistryPort(Protocol):
    def resolve(
        self, verify_channel: str, document_type: str, provider: str | None
    ) -> IdentityVerifyProviderPort:
        ...
