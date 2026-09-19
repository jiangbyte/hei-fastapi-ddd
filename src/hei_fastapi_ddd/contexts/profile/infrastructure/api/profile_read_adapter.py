"""Author: Charlie

ProfileReadPort 适配器。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.profile.application.api.profile_read_port import ProfileReadPort
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.admin_repository import (
    ProfileUserAdminRepositoryImpl,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_repository import (
    ProfileIdentityRepositoryImpl,
)
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_repository import (
    ProfileUserPortalRepositoryImpl,
)


class ProfileReadAdapter:
    def __init__(self, db: AsyncSession):
        self._admin = ProfileUserAdminRepositoryImpl(db)
        self._portal = ProfileUserPortalRepositoryImpl(db)
        self._identity = ProfileIdentityRepositoryImpl(db)

    async def list_admin_by_account_ids(self, account_ids: list[str]) -> list[dict]:
        return await self._admin.list_by_account_ids(account_ids)

    async def list_portal_by_account_ids(self, account_ids: list[str]) -> list[dict]:
        return await self._portal.list_by_account_ids(account_ids)

    async def is_identity_verified(self, account_id: str) -> bool:
        identity = await self._identity.get_by_account_id(account_id)
        return identity is not None and identity.status == "VERIFIED"

    async def get_profile_by_account(
        self, account_type: str, account_id: str
    ) -> dict[str, object] | None:
        if account_type == AccountType.ADMIN.value:
            return await self._admin.get_by_account_id(account_id)
        if account_type == AccountType.PORTAL.value:
            return await self._portal.get_by_account_id(account_id)
        return None

    async def get_profiles_by_account_ids(
        self, account_type: str, account_ids: list[str]
    ) -> dict[str, dict[str, object]]:
        if account_type == AccountType.ADMIN.value:
            rows = await self._admin.list_by_account_ids(account_ids)
        elif account_type == AccountType.PORTAL.value:
            rows = await self._portal.list_by_account_ids(account_ids)
        else:
            return {}
        return {str(row["account_id"]): row for row in rows}


def get_profile_read_port(db: AsyncSession) -> ProfileReadPort:
    return ProfileReadAdapter(db)
