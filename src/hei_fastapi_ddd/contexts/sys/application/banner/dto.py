"""展示图应用层 DTO。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from hei_fastapi_ddd.shared.web.pagination import PageQuery


class BannerCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    image: str
    target_account_types: list[str]
    category: str | None = None
    type: str | None = None
    position: str
    status: str = "ENABLED"
    sort: int = 0
    link_url: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class BannerUpdateCommand(BannerCreateCommand):
    id: str


class BannerAdminPageQuery(PageQuery):
    model_config = ConfigDict(extra="ignore")

    target_account_type: str | None = None
    category: str | None = None
    type: str | None = None
    position: str | None = None
    status: str | None = None


class BannerPublicListQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    position: str
    category: str | None = None
    type: str | None = None
