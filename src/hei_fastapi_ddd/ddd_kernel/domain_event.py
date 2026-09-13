"""领域事件基类。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """领域事件：记录聚合内已发生的业务事实。"""

    aggregate_id: Any
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
