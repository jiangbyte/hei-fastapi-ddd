"""反馈应用层 DTO。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from hei_fastapi_ddd.shared.web.pagination import PageQuery


class FeedbackCreateCommand(BaseModel):
    """提交反馈命令。"""

    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    content: str
    category: str | None = None
    contact: str | None = None
    attach_object_names: list[str] = Field(default_factory=list)


class FeedbackUpdateCommand(BaseModel):
    """处理反馈命令。"""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: str | None = None
    reply: str | None = None


class FeedbackAdminPageQuery(PageQuery):
    """管理端反馈分页。"""

    title: str | None = None
    category: str | None = None
    status: str | None = None
    submitter_account_type: str | None = None


class MyFeedbackPageQuery(PageQuery):
    """我的反馈分页。"""

    category: str | None = None
    status: str | None = None


class FeedbackIdQuery(BaseModel):
    """按 ID 查询。"""

    id: str


class FeedbackIdsCommand(BaseModel):
    """批量 ID。"""

    ids: list[str] = Field(default_factory=list)
