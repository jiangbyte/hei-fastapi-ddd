""" Author: Charlie

cg_test_order 仓储端口。
"""

from __future__ import annotations

from typing import Protocol

from hei_fastapi_ddd.contexts.biz.domain.cg_test_order.aggregate import CgTestOrder


class CgTestOrderRepository(Protocol):
    """cg_test_order 仓储协议。"""

    async def find_by_id(self, id: str) -> CgTestOrder | None:
        """按主键查找。"""
        ...

    async def save(self, entity: CgTestOrder) -> CgTestOrder:
        """持久化聚合。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...
