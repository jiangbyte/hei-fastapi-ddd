""" Author: Charlie

identity 仓储端口。
"""

from __future__ import annotations

from typing import Protocol

from hei_fastapi_ddd.contexts.profile.domain.identity.aggregate import IdentityCase


class IdentityCaseRepository(Protocol):
    """identity 仓储协议。"""

    async def find_by_id(self, id: str) -> IdentityCase | None:
        """按主键查找。"""
        ...

    async def save(self, entity: IdentityCase) -> IdentityCase:
        """持久化聚合。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...
