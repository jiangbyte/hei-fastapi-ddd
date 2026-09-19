"""IAM 账户标识只读适配（实现 sys domain 端口）。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import (
    AccountRepository,
)


class AccountIdentityReadAdapter:
    """将 IAM 仓储适配为 sys 只读端口。"""

    def __init__(self, db: AsyncSession):
        self._accounts = AccountRepository(db)

    async def list_identities_by_account_ids(
        self, account_ids: list[str]
    ) -> list[Mapping[str, Any]]:
        rows = await self._accounts.list_identities_by_account_ids(account_ids)
        return [
            {"identity_type": item.identity_type, "identifier": item.identifier}
            for item in rows
        ]
