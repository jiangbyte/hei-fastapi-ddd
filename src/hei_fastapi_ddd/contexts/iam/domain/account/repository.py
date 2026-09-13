""" Author: Charlie

账户仓储端口。
"""

from __future__ import annotations

from typing import Protocol

from hei_fastapi_ddd.contexts.iam.domain.account.aggregate import Account


class AccountDomainRepository(Protocol):
    """账户领域仓储协议（与基础设施 AccountRepository 并存，逐步收口）。"""

    async def find_by_id(self, id: str) -> Account | None:
        """按主键加载聚合。"""
        ...

    async def save(self, entity: Account) -> Account:
        """持久化聚合。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...
