""" Author: Charlie

portal 仓储端口。
"""

from __future__ import annotations

from typing import Protocol

from hei_fastapi_ddd.contexts.profile.domain.portal.aggregate import PortalProfile


class PortalProfileRepository(Protocol):
    """portal 仓储协议。"""

    async def find_by_id(self, id: str) -> PortalProfile | None:
        """按主键查找。"""
        ...

    async def save(self, entity: PortalProfile) -> PortalProfile:
        """持久化聚合。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...
