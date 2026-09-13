"""仓储协议：聚合持久化抽象。"""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar

ID = TypeVar("ID")
T = TypeVar("T")


class Repository(Protocol, Generic[T, ID]):
    """仓储接口：按标识加载与保存聚合，由基础设施层实现。"""

    async def find_by_id(self, id: ID) -> T | None:
        """按标识查找聚合；不存在时返回 None。"""
        ...

    async def save(self, entity: T) -> T:
        """持久化聚合（新增或更新），返回保存后的实体。"""
        ...
