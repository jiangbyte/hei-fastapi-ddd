"""cg_test_activity 应用层 DTO（非 HTTP 契约）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CgTestActivityCreateCommand(BaseModel):
    """创建活动命令。"""

    model_config = ConfigDict(extra="ignore")

    code: str
    name: str
    category: str | None = None
    type: str
    status: str
    cover_url: str | None = None
    description: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    max_participants: int
    price: float
    is_public: bool
    need_approval: bool
    rule_config: dict[str, Any]
    extra: dict[str, Any] | None = Field(default_factory=dict)


class CgTestActivityUpdateCommand(CgTestActivityCreateCommand):
    """更新活动命令。"""

    id: str


class CgTestActivityPageQuery(BaseModel):
    """活动分页查询。"""

    model_config = ConfigDict(extra="ignore")

    current: int = 1
    size: int = 20
    code: str | None = None
    name: str | None = None
    category: str | None = None
    type: str | None = None
    status: str | None = None

    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size
