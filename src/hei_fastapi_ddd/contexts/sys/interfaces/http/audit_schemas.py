""" Author: Charlie

操作审计相关 Schema：响应记录、写入载荷与分页查询参数。
"""

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.shared.web.pagination import PageQuery
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt


class OperationAuditRecord(ApiSchema):
    """操作审计日志响应记录（对齐 hei-boot SysOperationAuditLog）。"""

    id: str
    module: str
    resource_type: str | None = None
    resource_id: str | None = None
    action: str
    summary: str | None = None
    before_data: dict | None = None
    after_data: dict | None = None
    account_id: str | None = None
    account_type: str | None = None
    request_id: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    success: WireBool
    error_message: str | None = None
    operator_name: str | None = None
    action_name: str | None = None
    action_type: str | None = None
    module_label: str | None = None
    duration_ms: WireInt | None = None
    created_at: datetime


class OperationAuditCreate(ApiSchema):
    """操作审计日志写入载荷。"""

    module: str
    resource_type: str | None = None
    resource_id: str | None = None
    action: str
    summary: str | None = None
    before_data: dict | None = None
    after_data: dict | None = None
    account_id: str | None = None
    account_type: str | None = None
    request_id: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    success: WireBool = True
    error_message: str | None = None
    operator_name: str | None = None
    action_name: str | None = None
    action_type: str | None = None
    module_label: str | None = None
    duration_ms: WireInt | None = None


class OperationAuditPageQuery(PageQuery):
    """操作审计后台分页查询参数。"""

    module: str | None = Field(default=None, max_length=64)
    action: str | None = Field(default=None, max_length=64)
    exclude_action: str | None = Field(default=None, max_length=64)
    account_id: str | None = Field(default=None, max_length=64)
    success: WireBool | None = None
