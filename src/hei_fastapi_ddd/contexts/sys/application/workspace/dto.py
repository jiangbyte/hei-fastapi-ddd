"""工作台应用层 DTO。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceShortcutSaveCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resource_ids: list[str] = Field(default_factory=list)
