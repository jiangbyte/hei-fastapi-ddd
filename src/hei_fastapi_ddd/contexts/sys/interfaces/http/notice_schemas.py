""" Author: Charlie

消息通知请求与响应模型，含按类型（通知/公告）区分的校验逻辑。
"""

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from hei_fastapi_ddd.contexts.sys.application.notice.target_scope import (
    has_enabled_publish_location,
    validate_message_targets,
)
from hei_fastapi_ddd.contexts.sys.domain.notice.enums import NoticeKind
from hei_fastapi_ddd.shared.schema.base import ApiSchema, Id
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt
from hei_fastapi_ddd.shared.security.html_sanitize import sanitize_html
from hei_fastapi_ddd.shared.web.pagination import PageQuery


class SysNoticeCreateRequest(ApiSchema):
    """创建消息请求（content_type/severity/target_scope/status 可缺省，对齐 hei-boot 默认值）。

    发送者、撤回时间、浏览数为服务端维护字段，客户端不可伪造。
    """

    kind: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_type: str = "TEXT"
    category: str | None = None
    severity: str = "INFO"
    target_scope: str = "ALL"
    target_account_types: list[str] = Field(default_factory=list)
    target_account_ids: list[str] = Field(default_factory=list)
    target_dept_ids: list[str] = Field(default_factory=list)
    target_role_ids: list[str] = Field(default_factory=list)
    publish_locations: dict[str, Any] = Field(default_factory=dict)
    is_pinned: WireBool = False
    pinned_until: datetime | None = None
    source_type: str | None = None
    source_id: str | None = None
    status: str | None = None
    publish_at: datetime | None = None
    expire_at: datetime | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_by_kind(self):
        """按消息类型校验目标与发布位置等约束。"""
        kind = str(self.kind or "").upper()
        if kind not in {NoticeKind.NOTIFICATION.value, NoticeKind.ANNOUNCEMENT.value}:
            raise ValueError("kind 必须是 NOTIFICATION 或 ANNOUNCEMENT")
        self.kind = kind
        validate_message_targets(
            target_scope=self.target_scope,
            target_account_types=self.target_account_types,
            target_account_ids=self.target_account_ids,
            target_dept_ids=self.target_dept_ids,
            target_role_ids=self.target_role_ids,
        )
        if kind == NoticeKind.ANNOUNCEMENT.value:
            if not has_enabled_publish_location(self.publish_locations):
                raise ValueError("公告必须选择至少一个发布位置")
        else:
            if not (self.category or "").strip():
                raise ValueError("通知必须选择分类")
            self.publish_locations = self.publish_locations or {}
            self.is_pinned = False
            self.pinned_until = None
            self.expire_at = None
        self.content = sanitize_html(self.content_type, self.content) or self.content
        return self


class SysNoticeUpdateRequest(SysNoticeCreateRequest):
    """更新消息请求（在创建请求基础上增加 ID）。"""

    id: str = Field(min_length=1, max_length=64)


class SysNoticeAdminPageQuery(PageQuery):
    """管理端消息分页查询条件。"""

    title: str | None = None
    status: str | None = None
    kind: str | None = None


class NoticeReadRequest(ApiSchema):
    """标记已读请求。"""

    ids: list[Id] = Field(min_length=1)


class MyNoticePageQuery(PageQuery):
    """当前用户消息分页查询条件。"""

    title: str | None = None
    status: str | None = None
    kind: str | None = None


class PinNoticeRequest(ApiSchema):
    """公告置顶请求。"""

    id: Id
    is_pinned: WireBool
    pinned_until: datetime | None = None


class SysNoticeSchema(ApiSchema):
    """消息详情响应。"""

    id: str
    kind: str
    title: str
    content: str
    content_type: str
    category: str | None = None
    severity: str
    target_scope: str
    target_account_types: list[str] = Field(default_factory=list)
    target_account_ids: list[str] = Field(default_factory=list)
    target_dept_ids: list[str] = Field(default_factory=list)
    target_role_ids: list[str] = Field(default_factory=list)
    publish_locations: dict[str, Any] = Field(default_factory=dict)
    is_pinned: WireBool = False
    pinned_until: datetime | None = None
    sender_account_type: str | None = None
    sender_account_id: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    status: str
    publish_at: datetime | None = None
    revoked_at: datetime | None = None
    expire_at: datetime | None = None
    view_count: WireInt = 0
    extra: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None
    is_read: WireBool | None = None
