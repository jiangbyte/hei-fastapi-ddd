""" Author: Charlie

门户账户资料仓储层：封装扩展资料的初始化、写入与查询。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_po import ProfileUserPortal
from hei_fastapi_ddd.contexts.profile.interfaces.http.portal_schemas import ProfileUserPortalUpsertPayload


class ProfileUserPortalRepository:
    """门户账户资料仓储，负责门户资料主键写入与按账户查询。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_default(self, account_id: str) -> ProfileUserPortal:
        """为门户账户创建默认扩展资料记录。"""
        profile = ProfileUserPortal(account_id=account_id)
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def upsert(self, payload: ProfileUserPortalUpsertPayload) -> ProfileUserPortal:
        """创建或更新门户扩展资料。"""
        profile = await self.get_by_account_id(payload.account_id)
        if profile is None:
            profile = ProfileUserPortal(account_id=payload.account_id)
            self.db.add(profile)
        profile.nickname = payload.nickname
        profile.avatar = payload.avatar
        profile.signature = payload.signature
        profile.phone = payload.phone
        profile.email = payload.email
        await self.db.flush()
        return profile

    async def update_avatar(self, account_id: str, avatar: str) -> ProfileUserPortal:
        """只更新当前门户账户头像，避免覆盖其他资料字段。"""
        profile = await self.get_by_account_id(account_id)
        if profile is None:
            profile = ProfileUserPortal(account_id=account_id)
            self.db.add(profile)
        profile.avatar = avatar
        await self.db.flush()
        return profile

    async def get_by_account_id(self, account_id: str) -> ProfileUserPortal | None:
        """按账户 ID 查询门户资料记录。"""
        stmt = select(ProfileUserPortal).where(ProfileUserPortal.account_id == account_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_by_account_ids(self, account_ids: list[str]) -> list[ProfileUserPortal]:
        """批量查询门户扩展资料。"""
        unique_ids = list(dict.fromkeys(account_ids))
        if not unique_ids:
            return []
        stmt = select(ProfileUserPortal).where(ProfileUserPortal.account_id.in_(unique_ids))
        return list((await self.db.execute(stmt)).scalars().all())
