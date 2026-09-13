""" Author: Charlie

管理端账户资料仓储层：封装扩展资料的初始化、写入与查询。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.admin_po import ProfileUserAdmin
from hei_fastapi_ddd.contexts.profile.interfaces.http.admin_schemas import ProfileUserAdminUpsertPayload


class ProfileUserAdminRepository:
    """管理端账户资料仓储，负责扩展资料的初始化与查询。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_default(self, account_id: str) -> ProfileUserAdmin:
        """为管理端账户创建默认扩展资料记录。"""
        profile = ProfileUserAdmin(account_id=account_id)
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def upsert(self, payload: ProfileUserAdminUpsertPayload) -> ProfileUserAdmin:
        """创建或更新管理端扩展资料。"""
        profile = await self.get_by_account_id(payload.account_id)
        if profile is None:
            profile = ProfileUserAdmin(account_id=payload.account_id)
            self.db.add(profile)
        profile.nickname = payload.nickname
        profile.avatar = payload.avatar
        profile.signature = payload.signature
        profile.phone = payload.phone
        profile.email = payload.email
        profile.remark = payload.remark
        await self.db.flush()
        return profile

    async def update_avatar(self, account_id: str, avatar: str) -> ProfileUserAdmin:
        """只更新当前管理端账户头像，避免覆盖其他资料字段。"""
        profile = await self.get_by_account_id(account_id)
        if profile is None:
            profile = ProfileUserAdmin(account_id=account_id)
            self.db.add(profile)
        profile.avatar = avatar
        await self.db.flush()
        return profile

    async def get_by_account_id(self, account_id: str) -> ProfileUserAdmin | None:
        """按账户 ID 查询管理端扩展资料。"""
        stmt = select(ProfileUserAdmin).where(ProfileUserAdmin.account_id == account_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_by_account_ids(self, account_ids: list[str]) -> list[ProfileUserAdmin]:
        """批量查询管理端扩展资料。"""
        unique_ids = list(dict.fromkeys(account_ids))
        if not unique_ids:
            return []
        stmt = select(ProfileUserAdmin).where(ProfileUserAdmin.account_id.in_(unique_ids))
        return list((await self.db.execute(stmt)).scalars().all())
