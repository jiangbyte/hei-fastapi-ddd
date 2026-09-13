""" Author: Charlie

notice 领域实体。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hei_fastapi_ddd.ddd_kernel.domain_exception import DomainException
from hei_fastapi_ddd.ddd_kernel.entity import AggregateRoot


@dataclass
class Notice(AggregateRoot[str]):
    """notice 聚合根，承载基础状态校验。"""

    id: str
    status: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self, self.id)

    def ensure_required(self, *fields: str) -> None:
        """校验必填字段非空。"""
        # 1. 逐字段检查
        for name in fields:
            value = getattr(self, name, None) if hasattr(self, name) else self.extra.get(name)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise DomainException(f"{name} is required")

    def change_status(self, new_status: str, *, allowed: set[str] | None = None) -> None:
        """变更状态；可选限制合法目标集合。"""
        # 1. 校验目标状态
        if allowed is not None and new_status not in allowed:
            raise DomainException(f"Invalid status transition to {new_status}")
        # 2. 写入新状态
        self.status = new_status
