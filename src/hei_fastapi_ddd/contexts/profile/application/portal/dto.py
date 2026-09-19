"""Author: Charlie

门户用户中心应用层命令/结果。
"""

from __future__ import annotations

from pydantic import Field

from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.common_schema import IdNameResponse


class PortalProfileUpsertCommand(ApiSchema):
    account_id: str
    nickname: str | None = None
    avatar: str | None = None
    signature: str | None = None
    phone: str | None = None
    email: str | None = None
    bio: str | None = None
    level: str | None = None


class PortalUserCenterProfileUpdateCommand(ApiSchema):
    nickname: str | None = None
    avatar: str | None = None
    signature: str | None = None
    bio: str | None = None


class PortalUserCenterPasswordUpdateCommand(ApiSchema):
    old_password: str | None = None
    otp_code: str | None = None
    new_password: str = Field(min_length=1, max_length=512)


class PortalUserCenterPhoneUpdateCommand(ApiSchema):
    phone: str | None = None
    password: str
    phone_login_enabled: bool = False
    otp_code: str | None = None


class PortalUserCenterEmailUpdateCommand(ApiSchema):
    email: str | None = None
    password: str
    email_login_enabled: bool = False
    otp_code: str | None = None


class PortalPublicSpaceQueryCommand(ApiSchema):
    account_id: str


class PortalPublicProfileResult(ApiSchema):
    account_id: str
    nickname: str | None = None
    avatar: str | None = None
    signature: str | None = None
    bio: str | None = None


class PortalUserCenterAvatarUpdateResult(ApiSchema):
    avatar: str
    file_id: str
    object_name: str
    url: str
