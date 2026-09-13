"""实体与聚合根基类。"""

from __future__ import annotations

from typing import Generic, TypeVar

from hei_fastapi_ddd.ddd_kernel.domain_event import DomainEvent

ID = TypeVar("ID")


class Entity(Generic[ID]):
    """领域实体：以唯一标识区分同一性，而非属性值。"""

    def __init__(self, id: ID) -> None:
        self.id = id

    def __eq__(self, other: object) -> bool:
        # 1. 非同类实体直接判定不等
        if not isinstance(other, Entity):
            return NotImplemented
        # 2. 仅按标识比较，忽略其余属性
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class AggregateRoot(Entity[ID]):
    """聚合根：实体边界入口，负责收集待发布的领域事件。"""

    def __init__(self, id: ID) -> None:
        super().__init__(id)
        self._domain_events: list[DomainEvent] = []

    def add_domain_event(self, event: DomainEvent) -> None:
        """向聚合追加一条领域事件，待事务提交后向外发布。"""
        self._domain_events.append(event)

    def pull_domain_events(self) -> list[DomainEvent]:
        """取出并清空已收集的领域事件，避免重复发布。"""
        # 1. 复制当前事件列表作为返回值
        events = list(self._domain_events)
        # 2. 清空内部缓冲，保证幂等拉取
        self._domain_events.clear()
        # 3. 返回副本供基础设施层派发
        return events
