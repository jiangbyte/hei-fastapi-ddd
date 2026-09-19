""" Author: Charlie

工作台 API Schema（对齐 hei-boot workspace 模块）。
"""

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt


class WorkspaceShortcutSaveRequest(ApiSchema):
    """保存快捷应用请求（对齐 WorkspaceShortcutSaveParam）。"""

    resource_ids: list[str] = Field(default_factory=list)


class WorkspaceShortcutResult(ApiSchema):
    """快捷应用项（对齐 WorkspaceShortcutResult）。"""

    id: str | None = None
    resource_id: str
    sort: WireInt | None = None
    name: str | None = None
    path: str | None = None
    icon: str | None = None
    code: str | None = None
    resource_type: str | None = None
    status: str | None = None


class WorkspaceActivityItem(ApiSchema):
    """工作台近期活动项（对齐 WorkspaceActivityItemResult）。"""

    id: str | None = None
    module: str | None = None
    module_label: str | None = None
    action: str | None = None
    action_name: str | None = None
    action_type: str | None = None
    summary: str | None = None
    success: WireBool | None = None
    ip: str | None = None
    user_agent: str | None = None
    operator_name: str | None = None
    duration_ms: WireInt | None = None
    resource_id: str | None = None
    created_at: datetime | None = None


class WorkspaceOverviewResponse(ApiSchema):
    """工作台总览（对齐 WorkspaceOverviewResult）。"""

    shortcuts: list[WorkspaceShortcutResult] = Field(default_factory=list)
    recent_operations: list[WorkspaceActivityItem] = Field(default_factory=list)
    recent_logins: list[WorkspaceActivityItem] = Field(default_factory=list)
