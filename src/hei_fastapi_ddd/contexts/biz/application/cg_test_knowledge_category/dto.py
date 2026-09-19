"""cg_test_knowledge_category 应用层 DTO。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CgTestKnowledgeCategoryCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    parent_id: str | None = None
    code: str
    name: str
    status: str
    sort: int
    is_visible: bool
    description: str | None = None
    extra: dict[str, Any]


class CgTestKnowledgeCategoryUpdateCommand(CgTestKnowledgeCategoryCreateCommand):
    id: str


class CgTestKnowledgeCategoryPageQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current: int = 1
    size: int = 20
    code: str | None = None
    name: str | None = None
    status: str | None = None

    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size


class CgTestKnowledgeCategoryKeywordQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    keyword: str | None = None


class CgTestKnowledgeDocCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category_id: str
    code: str
    title: str
    type: str
    status: str
    summary: str | None = None
    content: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    view_count: int
    sort: int
    is_top: bool
    settings: dict[str, Any]
    extra: dict[str, Any] | None = Field(default_factory=dict)


class CgTestKnowledgeDocUpdateCommand(CgTestKnowledgeDocCreateCommand):
    id: str


class CgTestKnowledgeDocPageQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current: int = 1
    size: int = 20
    category_id: str | None = None
    code: str | None = None
    title: str | None = None
    type: str | None = None
    status: str | None = None

    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size
