"""dept 应用层 DTO。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeptCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    category: str
    parent_id: str | None = None
    master_id: str | None = None
    deputy_master_id: str | None = None
    sort: int = 99
    is_virtual: bool = False
    status: str = "ENABLED"
    extra: dict[str, Any] = Field(default_factory=dict)


class DeptUpdateCommand(DeptCreateCommand):
    id: str


class DeptPageQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current: int = 1
    size: int = 20
    name: str | None = None
    category: str | None = None
    parent_id: str | None = None
    status: str | None = None

    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size
