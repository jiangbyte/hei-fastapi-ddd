"""cg_test_catalog 应用层 DTO（非 HTTP 契约）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class CgTestCatalogCreateCommand(BaseModel):
    """创建目录命令。"""

    model_config = ConfigDict(extra="ignore")

    parent_id: str | None = None
    code: str
    name: str
    category: str | None = None
    status: str
    sort: int
    is_visible: bool
    icon: str | None = None
    description: str | None = None
    extra: dict[str, Any]


class CgTestCatalogUpdateCommand(CgTestCatalogCreateCommand):
    """更新目录命令。"""

    id: str


class CgTestCatalogPageQuery(BaseModel):
    """目录分页查询。"""

    model_config = ConfigDict(extra="ignore")

    current: int = 1
    size: int = 20
    code: str | None = None
    name: str | None = None
    category: str | None = None
    status: str | None = None

    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size


class CgTestCatalogKeywordQuery(BaseModel):
    """目录关键字查询。"""

    model_config = ConfigDict(extra="ignore")

    keyword: str | None = None
