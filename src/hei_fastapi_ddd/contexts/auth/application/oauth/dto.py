"""Author: Charlie

OAuth 应用层结果模型（与 HTTP api schema 解耦）。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool


class OauthBindingResult(ApiSchema):
    provider: str
    label: str
    open_id_masked: str
    nickname: str | None = None
    avatar: str | None = None
    bound_at: datetime | None = None


class OauthProviderOptionResult(ApiSchema):
    provider: str
    label: str
    enabled: WireBool = False
    web_oauth: WireBool = True
