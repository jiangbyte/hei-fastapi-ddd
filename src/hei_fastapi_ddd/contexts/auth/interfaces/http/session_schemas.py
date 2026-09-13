""" Author: Charlie

会话管理请求/响应模型：会话分析、分页查询、token 信息与下线请求等模型。
"""

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt
from hei_fastapi_ddd.shared.web.pagination import PageQuery


class SessionAnalysisResponse(ApiSchema):
    """在线会话统计概览响应（数值按字符串线格式输出）。"""

    online_account_count: WireInt
    online_token_count: WireInt
    admin_account_count: WireInt
    portal_account_count: WireInt
    one_hour_new_count: WireInt
    max_token_count: WireInt


class SessionPageQuery(PageQuery):
    """会话分页查询参数。"""

    size: WireInt = Field(default=20, ge=1, le=200)

    account_type: AccountType | None = None
    account_id: str | None = Field(default=None, max_length=64)
    account: str | None = Field(default=None, max_length=128)
    ip: str | None = Field(default=None, max_length=64)
    keyword: str | None = Field(default=None, max_length=128)


class SessionTokenInfo(ApiSchema):
    """单个在线 token 信息。"""

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
    """账户维度的在线会话聚合项。"""

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
    """按账户类型与账户 ID 定位会话（account_type 缺省按 ADMIN 处理，对齐 hei-boot）。"""

    account_type: AccountType | None = None
    account_id: str = Field(min_length=1, max_length=64)


class SessionExitRequest(ApiSchema):
    """按账户批量下线请求。"""

    targets: list[SessionTokensQuery] = Field(min_length=1)


class SessionTokenExitRequest(ApiSchema):
    """按 token 批量下线请求。"""

    tokens: list[str] = Field(min_length=1)
