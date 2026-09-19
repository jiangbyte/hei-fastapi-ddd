"""Author: Charlie

账户密码历史仓储：供密码策略校验与记录。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.password_history_po import (
    SysAccountPasswordHistory,
)
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.security.password import hash_password_async, verify_password_async


class PasswordHistoryRepositoryImpl:
    """密码历史读写。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_recent_hashes(self, account_id: str, limit: int) -> list[str]:
        if limit <= 0:
            return []
        stmt = (
            select(SysAccountPasswordHistory.password_hash)
            .where(SysAccountPasswordHistory.account_id == account_id)
            .order_by(SysAccountPasswordHistory.created_at.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def append(
        self,
        account_id: str,
        plain_password: str,
        *,
        changed_by: str | None,
        change_reason: str | None,
    ) -> None:
        self.db.add(
            SysAccountPasswordHistory(
                id=generate_snowflake_id(),
                account_id=account_id,
                password_hash=await hash_password_async(plain_password),
                changed_by=changed_by or account_id,
                change_reason=change_reason or "unknown",
            )
        )

    async def get_latest_changed_at(self, account_id: str):
        stmt = (
            select(SysAccountPasswordHistory.created_at)
            .where(SysAccountPasswordHistory.account_id == account_id)
            .order_by(SysAccountPasswordHistory.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def matches_any_history(self, account_id: str, plain_password: str, limit: int) -> bool:
        for old_hash in await self.list_recent_hashes(account_id, limit):
            if await verify_password_async(plain_password, old_hash):
                return True
        return False
