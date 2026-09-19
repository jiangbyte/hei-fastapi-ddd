"""Author: Charlie

ProfileUpsertPort 适配器：委托 profile 基础设施仓储完成 upsert。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.profile.application.api.profile_upsert_port import ProfileUpsertPort
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.admin_repository import (
    ProfileUserAdminRepositoryImpl,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_repository import (
    ProfileUserPortalRepositoryImpl,
)


class ProfileUpsertAdapter:
    """将 profile 仓储适配为 ProfileUpsertPort。"""

    def __init__(self, db: AsyncSession):
        self._admin = ProfileUserAdminRepositoryImpl(db)
        self._portal = ProfileUserPortalRepositoryImpl(db)

    async def upsert_admin_profile(self, data: Mapping[str, Any]) -> None:
        await self._admin.upsert(data)

    async def upsert_portal_profile(self, data: Mapping[str, Any]) -> None:
        await self._portal.upsert(data)


def get_profile_upsert_port(db: AsyncSession) -> ProfileUpsertPort:
    """工厂：返回资料 upsert 端口。"""
    return ProfileUpsertAdapter(db)
