"""role 应用层 DTO。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from hei_fastapi_ddd.contexts.iam.domain.enums import RoleScopeType
from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum


class RoleCreateCommand(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str
    name: str
    category: str
    scope_type: RoleScopeType = RoleScopeType.PLATFORM
    owner_dept_id: str | None = None
    sort: int = 99
    status: StatusEnum = StatusEnum.ENABLED
    is_builtin: bool = False
    description: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class RoleUpdateCommand(RoleCreateCommand):
    id: str


class RolePageQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current: int = 1
    size: int = 20
    code: str | None = None
    name: str | None = None
    category: str | None = None
    scope_type: RoleScopeType | None = None
    status: str | None = None

    @property
    def offset(self) -> int:
        return max(self.current - 1, 0) * self.size


class RoleResourceGrantItem(BaseModel):
    resource_id: str
    permission_keys: list[str] = Field(default_factory=list)


class RoleGrantResourceCommand(BaseModel):
    id: str
    account_type: AccountType = AccountType.ADMIN
    grant_info_list: list[RoleResourceGrantItem] = Field(default_factory=list)


class RoleGrantClientResourceCommand(RoleGrantResourceCommand):
    pass


class RoleGrantUserCommand(BaseModel):
    id: str
    account_ids: list[str] = Field(default_factory=list)


class RoleOwnResourceQuery(BaseModel):
    id: str
    account_type: AccountType | None = None


class RoleOwnClientResourceQuery(RoleOwnResourceQuery):
    pass
