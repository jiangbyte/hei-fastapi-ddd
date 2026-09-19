"""Author: Charlie

会话管理应用层查询/结果模型。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt
from hei_fastapi_ddd.shared.web.pagination import PageQuery


class SessionAnalysisResult(ApiSchema):
    online_account_count: WireInt
    online_token_count: WireInt
    admin_account_count: WireInt
    portal_account_count: WireInt
    one_hour_new_count: WireInt
    max_token_count: WireInt


class SessionPageQuery(PageQuery):
    size: WireInt = Field(default=20, ge=1, le=200)
    account_type: AccountType | None = None
    account_id: str | None = Field(default=None, max_length=64)
    account: str | None = Field(default=None, max_length=128)
    ip: str | None = Field(default=None, max_length=64)
    keyword: str | None = Field(default=None, max_length=128)


class SessionTokenInfo(ApiSchema):
    token: str
    account_id: str | None = None
    account_type: AccountType | str | None = None
    remember_me: WireBool = True
    device_label: str | None = None
    client_ip: str | None = None
    user_agent: str | None = None
    login_at: datetime | None = None
    last_active_at: datetime | None = None
    expires_at: datetime | None = None


class SessionAccountItem(ApiSchema):
    account_id: str
    account_type: AccountType | str
    account: str
    name: str | None = None
    nickname: str | None = None
    avatar: str | None = None
    latest_login_ip: str | None = None
    latest_login_time: datetime | None = None
    client_ip: str | None = None
    device_label: str | None = None
    token_count: WireInt
    first_login_at: datetime | None = None
    latest_active_at: datetime | None = None
    tokens: list[SessionTokenInfo] = Field(default_factory=list)


class SessionTokensQuery(ApiSchema):
    account_type: AccountType | None = None
    account_id: str = Field(min_length=1, max_length=64)
