""" Author: Charlie

审计辅助：解析操作主体登录名等。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import AccountRepository
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType


async def resolve_account_login(db: AsyncSession, account_id: str | None) -> str | None:
    """按账号 ID 解析主登录名（优先 ACCOUNT 类型标识）。"""
    if not account_id or not str(account_id).strip():
        return None
    identities = await AccountRepository(db).list_identities_by_account_ids([account_id])
    preferred = (
        AccountIdentityType.ACCOUNT.value,
        AccountIdentityType.EMAIL.value,
        AccountIdentityType.PHONE.value,
    )
    for identity_type in preferred:
        for item in identities:
            if item.identity_type == identity_type and str(item.identifier).strip():
                return str(item.identifier).strip()
    return None
