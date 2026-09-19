""" Author: Charlie

管理端账户资料仓储实现（不依赖 api Schema）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.admin_po import ProfileUserAdmin


def _row(entity: ProfileUserAdmin) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class ProfileUserAdminRepositoryImpl:
    """管理端账户资料仓储实现。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_default(self, account_id: str) -> dict[str, Any]:
        profile = ProfileUserAdmin(account_id=account_id)
        self.db.add(profile)
        await self.db.flush()
        return _row(profile)

    async def upsert(self, data: Mapping[str, Any]) -> dict[str, Any]:
        account_id = str(data["account_id"])
        profile = await self.get_by_account_id(account_id)
        if profile is None:
            entity = ProfileUserAdmin(account_id=account_id)
            self.db.add(entity)
        else:
            entity = await self._get_entity(account_id)
            assert entity is not None
        entity.nickname = data.get("nickname")
        entity.avatar = data.get("avatar")
        entity.signature = data.get("signature")
        entity.phone = data.get("phone")
        entity.email = data.get("email")
        entity.remark = data.get("remark")
        await self.db.flush()
        return _row(entity)

    async def update_avatar(self, account_id: str, avatar: str) -> dict[str, Any]:
        entity = await self._get_entity(account_id)
        if entity is None:
            entity = ProfileUserAdmin(account_id=account_id)
            self.db.add(entity)
        entity.avatar = avatar
        await self.db.flush()
        return _row(entity)

    async def get_by_account_id(self, account_id: str) -> dict[str, Any] | None:
        entity = await self._get_entity(account_id)
        return _row(entity) if entity is not None else None

    async def list_by_account_ids(self, account_ids: list[str]) -> list[dict[str, Any]]:
        unique_ids = list(dict.fromkeys(account_ids))
        if not unique_ids:
            return []
        stmt = select(ProfileUserAdmin).where(ProfileUserAdmin.account_id.in_(unique_ids))
        return [_row(item) for item in (await self.db.execute(stmt)).scalars().all()]

    async def _get_entity(self, account_id: str) -> ProfileUserAdmin | None:
        stmt = select(ProfileUserAdmin).where(ProfileUserAdmin.account_id == account_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()


ProfileUserAdminRepository = ProfileUserAdminRepositoryImpl
