"""account 应用层 DTO。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType


class AccountCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    account: str
    password: str
    password_key_id: str | None = None
    account_type: AccountType
    account_status: AccountStatusEnum = AccountStatusEnum.ENABLED
    nickname: str | None = None
    avatar: str | None = None
    signature: str | None = None
    phone: str | None = None
    email: str | None = None
    remark: str | None = None


class AccountUpdateCommand(AccountCreateCommand):
    id: str
    password: str | None = None


class AccountUpdateLoginIdentityCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    email_login_enabled: bool = False
    email: str | None = None
    phone_login_enabled: bool = False
    phone: str | None = None


class AccountPageQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current: int = 1
    size: int = 20
    account: str | None = None
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    account_type: AccountType | None = None
    account_status: AccountStatusEnum | None = None

    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size


class AccountResourceGrantItem(BaseModel):
    resource_id: str
    permission_keys: list[str] = Field(default_factory=list)


class AccountDeptGrantItem(BaseModel):
    dept_id: str
    is_primary: bool = False


class AccountGrantResourceCommand(BaseModel):
    id: str
    grant_info_list: list[AccountResourceGrantItem] = Field(default_factory=list)


class AccountGrantClientResourceCommand(AccountGrantResourceCommand):
    pass


class AccountGrantRoleCommand(BaseModel):
    id: str
    role_ids: list[str] = Field(default_factory=list)


class AccountGrantGroupCommand(BaseModel):
    id: str
    group_ids: list[str] = Field(default_factory=list)


class AccountGrantDeptCommand(BaseModel):
    id: str
    grant_info_list: list[AccountDeptGrantItem] = Field(default_factory=list)


class AccountOwnQuery(BaseModel):
    id: str


def grant_items_to_dicts(items: list[BaseModel]) -> list[dict[str, Any]]:
    return [item.model_dump() for item in items]
