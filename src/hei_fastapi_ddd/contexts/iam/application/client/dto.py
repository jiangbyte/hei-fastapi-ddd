"""client 应用层 DTO。"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class ClientCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    code: str | None = None
    status: str = "ENABLED"
    sort: int = 99
    owner_dept_id: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

class ClientUpdateCommand(ClientCreateCommand):
    id: str

class ClientPageQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")
    current: int = 1
    size: int = 20
    name: str | None = None
    code: str | None = None
    status: str | None = None
    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size
