"""position 应用层 DTO（非 HTTP 契约）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PositionCreateCommand(BaseModel):
    """创建职位命令。"""

    model_config = ConfigDict(extra="ignore")

    name: str
    category: str
    status: str
    sort: int = 0
    owner_dept_id: str | None = None
    extra: dict[str, Any] | None = Field(default_factory=dict)


class PositionUpdateCommand(PositionCreateCommand):
    """更新职位命令。"""

    id: str


class PositionPageQuery(BaseModel):
    """职位分页查询。"""

    model_config = ConfigDict(extra="ignore")

    current: int = 1
    size: int = 20
    name: str | None = None
    category: str | None = None
    status: str | None = None

    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size
