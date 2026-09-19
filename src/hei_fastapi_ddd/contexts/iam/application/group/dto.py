"""group 应用层 DTO。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum


class GroupCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    owner_dept_id: str | None = None
    description: str | None = None
    status: StatusEnum = StatusEnum.ENABLED
    extra: dict[str, Any] = Field(default_factory=dict)


class GroupUpdateCommand(GroupCreateCommand):
    id: str


class GroupPageQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current: int = 1
    size: int = 20
    name: str | None = None
    status: str | None = None

    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size


class GroupResourceGrantItem(BaseModel):
    resource_id: str
    permission_keys: list[str] = Field(default_factory=list)


class GroupGrantResourceCommand(BaseModel):
    id: str
    account_type: AccountType = AccountType.ADMIN
    grant_info_list: list[GroupResourceGrantItem] = Field(default_factory=list)


class GroupGrantClientResourceCommand(GroupGrantResourceCommand):
    pass


class GroupGrantRoleCommand(BaseModel):
    id: str
    account_type: AccountType = AccountType.ADMIN
    role_ids: list[str] = Field(default_factory=list)


class GroupGrantUserCommand(BaseModel):
    id: str
    account_ids: list[str] = Field(default_factory=list)


class GroupOwnRoleQuery(BaseModel):
    id: str
    account_type: AccountType | None = None


class GroupOwnResourceQuery(BaseModel):
    id: str
    account_type: AccountType | None = None


class GroupOwnClientResourceQuery(GroupOwnResourceQuery):
    pass
