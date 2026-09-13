""" Author: Charlie

用户资料批量查询工具。
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.admin_po import ProfileUserAdmin
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.admin_repository import ProfileUserAdminRepository
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_po import ProfileUserPortal
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_repository import ProfileUserPortalRepository


def as_account_type(account_type: AccountType | str) -> AccountType:
    """将账户类型归一化为 AccountType 枚举，非法值抛 BusinessError。"""
    if isinstance(account_type, AccountType):
        return account_type
    try:
        return AccountType(str(account_type))
    except ValueError as exc:
        raise BusinessError(f"Unsupported account type: {account_type}") from exc


def pick_profile_repo(db: AsyncSession, account_type: AccountType | str):
    """按账户类型返回对应的资料仓储实例。"""
    account_type = as_account_type(account_type)
    match account_type:
        case AccountType.ADMIN:
            return ProfileUserAdminRepository(db)
        case AccountType.PORTAL:
            return ProfileUserPortalRepository(db)
        case _:
            raise BusinessError(f"Unsupported account type for profile: {account_type}")


def pick_profile_model(account_type: AccountType | str):
    """按账户类型返回对应的资料模型类。"""
    account_type = as_account_type(account_type)
    match account_type:
        case AccountType.ADMIN:
            return ProfileUserAdmin
        case AccountType.PORTAL:
            return ProfileUserPortal
        case _:
            raise BusinessError(f"Unsupported account type for profile: {account_type}")


async def get_profile(
    db: AsyncSession, account_type: AccountType | str, account_id: str
) -> object | None:
    """按账户类型与 ID 查询资料记录，不存在时返回 None。"""
    repo = pick_profile_repo(db, account_type)
    return await repo.get_by_account_id(account_id)


async def get_profiles_batch(
    db: AsyncSession,
    account_type: AccountType | str,
    account_ids: list[str],
) -> dict[str, object]:
    """批量查询资料记录，返回以 account_id 为键的字典。"""
    if not account_ids:
        return {}
    repo = pick_profile_repo(db, account_type)
    profiles = await repo.list_by_account_ids(list(dict.fromkeys(account_ids)))
    return {p.account_id: p for p in profiles}
