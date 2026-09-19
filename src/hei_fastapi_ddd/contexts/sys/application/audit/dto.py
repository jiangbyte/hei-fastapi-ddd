"""审计应用层 DTO。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from hei_fastapi_ddd.shared.web.pagination import PageQuery


class OperationAuditCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    module: str
    resource_type: str | None = None
    resource_id: str | None = None
    action: str
    summary: str | None = None
    before_data: dict[str, Any] | None = None
    after_data: dict[str, Any] | None = None
    account_id: str | None = None
    account_type: str | None = None
    request_id: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    success: bool = True
    error_message: str | None = None
    operator_name: str | None = None
    action_name: str | None = None
    action_type: str | None = None
    module_label: str | None = None
    duration_ms: int | None = None


class OperationAuditPageQuery(PageQuery):
    model_config = ConfigDict(extra="ignore")

    module: str | None = None
    action: str | None = None
    exclude_action: str | None = None
    account_id: str | None = None
    success: bool | None = None
