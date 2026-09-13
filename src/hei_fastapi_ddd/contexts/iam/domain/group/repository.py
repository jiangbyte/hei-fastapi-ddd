""" Author: Charlie

group 仓储端口。
"""

from __future__ import annotations

from typing import Protocol

from hei_fastapi_ddd.contexts.iam.domain.group.aggregate import Group


class GroupRepository(Protocol):
    """group 仓储协议。"""

    async def find_by_id(self, id: str) -> Group | None:
        """按主键查找。"""
        ...

    async def save(self, entity: Group) -> Group:
        """持久化聚合。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...
