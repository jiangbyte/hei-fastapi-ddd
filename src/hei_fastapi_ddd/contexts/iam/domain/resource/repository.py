""" Author: Charlie

resource 仓储端口。
"""

from __future__ import annotations

from typing import Protocol

from hei_fastapi_ddd.contexts.iam.domain.resource.aggregate import Resource


class ResourceRepository(Protocol):
    """resource 仓储协议。"""

    async def find_by_id(self, id: str) -> Resource | None:
        """按主键查找。"""
        ...

    async def save(self, entity: Resource) -> Resource:
        """持久化聚合。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...
