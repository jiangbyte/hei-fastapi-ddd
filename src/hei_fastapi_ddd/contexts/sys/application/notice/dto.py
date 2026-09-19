"""消息通知应用层 DTO。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from hei_fastapi_ddd.shared.web.pagination import PageQuery


class NoticeCreateCommand(BaseModel):
    """创建消息命令。"""

    model_config = ConfigDict(extra="ignore")

    kind: str
    title: str
    content: str
    content_type: str = "TEXT"
    category: str | None = None
    severity: str = "INFO"
    target_scope: str = "ALL"
    target_account_types: list[str] = Field(default_factory=list)
    target_account_ids: list[str] = Field(default_factory=list)
    target_dept_ids: list[str] = Field(default_factory=list)
    target_role_ids: list[str] = Field(default_factory=list)
    publish_locations: dict[str, Any] = Field(default_factory=dict)
    is_pinned: bool = False
    pinned_until: datetime | None = None
    source_type: str | None = None
    source_id: str | None = None
    status: str | None = None
    publish_at: datetime | None = None
    expire_at: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class NoticeUpdateCommand(NoticeCreateCommand):
    """更新消息命令。"""

    id: str


class NoticeAdminPageQuery(PageQuery):
    """管理端分页。"""

    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    status: str | None = None
    kind: str | None = None


class MyNoticePageQuery(PageQuery):
    """当前用户消息分页。"""

    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    status: str | None = None
    kind: str | None = None


class NoticeReadCommand(BaseModel):
    """标记已读。"""

    model_config = ConfigDict(extra="ignore")

    ids: list[str] = Field(min_length=1)


class PinNoticeCommand(BaseModel):
    """置顶公告。"""

    model_config = ConfigDict(extra="ignore")

    id: str
    is_pinned: bool
    pinned_until: datetime | None = None
