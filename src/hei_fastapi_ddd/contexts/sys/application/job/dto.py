"""定时任务应用层 DTO。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from hei_fastapi_ddd.shared.web.pagination import PageQuery


class JobCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    handler: str
    trigger_type: str
    trigger_config: str
    params: dict[str, Any] | None = None
    enabled: bool = True
    sort: int = 0
    remark: str | None = None


class JobUpdateCommand(JobCreateCommand):
    id: str


class JobEnabledCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    enabled: bool


class JobAdminPageQuery(PageQuery):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    trigger_type: str | None = None
    enabled: bool | None = None


class JobLogAdminPageQuery(PageQuery):
    model_config = ConfigDict(extra="ignore")

    job_id: str | None = None
    success: bool | None = None
