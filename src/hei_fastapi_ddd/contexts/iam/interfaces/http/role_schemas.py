""" Author: Charlie

角色 Schema：角色创建/更新/分页查询及资源授权相关请求与响应结构。
"""

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.contexts.iam.domain.enums import RoleScopeType
from hei_fastapi_ddd.contexts.iam.interfaces.http.iam_schemas import (
    ResourceGrantModuleOption,
    SysAccountSchema,
)
from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum
from hei_fastapi_ddd.shared.schema.base import ApiSchema, IdQuery
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt
from hei_fastapi_ddd.shared.web.pagination import PageQuery


class RoleCreateRequest(ApiSchema):
    """创建角色请求。"""

    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    category: str = Field(min_length=1, max_length=64)
    scope_type: RoleScopeType = RoleScopeType.PLATFORM
    owner_dept_id: str | None = Field(default=None, max_length=64)
    sort: WireInt = 99
    status: StatusEnum = StatusEnum.ENABLED
    is_builtin: WireBool = False
    description: str | None = None
    extra: dict = Field(default_factory=dict)


class RoleUpdateRequest(RoleCreateRequest):
    """更新角色请求。"""

    id: str = Field(min_length=1, max_length=64)


class RoleAdminPageQuery(PageQuery):
    """角色管理端分页查询条件。"""

    code: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=64)
    category: str | None = Field(default=None, max_length=64)
    scope_type: RoleScopeType | None = None
    status: str | None = Field(default=None, max_length=32)


class SysRoleSchema(ApiSchema):
    """角色响应结构，含所属部门名称与创建人昵称回显。"""

    id: str
    code: str
    name: str
    category: str
    scope_type: RoleScopeType
    owner_dept_id: str | None = None
    sort: WireInt
    status: str
    is_builtin: WireBool
    description: str | None = None
    extra: dict
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None
    owner_dept_name: str | None = None
    created_name: str | None = None
    updated_name: str | None = None


class RoleResourceGrantInfo(ApiSchema):
    """角色资源授权项结构。"""

    resource_id: str = Field(min_length=1, max_length=64)
    permission_keys: list[str] = Field(default_factory=list)


class RoleOwnResourceQuery(IdQuery):
    """角色资源查询条件（附带账户体系，缺省不过滤，对齐 hei-boot）。"""

    account_type: AccountType | None = None


class RoleOwnResourceResponse(ApiSchema):
    """角色拥有的资源响应结构。"""

    id: str
    modules: list[ResourceGrantModuleOption] = Field(default_factory=list)
    grant_info_list: list[RoleResourceGrantInfo] = Field(default_factory=list)


class RoleGrantResourceRequest(ApiSchema):
    """给角色授权资源的请求（account_type 缺省按 ADMIN，对齐 hei-boot）。"""

    id: str = Field(min_length=1, max_length=64)
    account_type: AccountType = AccountType.ADMIN
    grant_info_list: list[RoleResourceGrantInfo] = Field(default_factory=list)


class RoleOwnClientResourceQuery(IdQuery):
    """角色客户端资源查询条件（附带账户体系，缺省不过滤，对齐 hei-boot）。"""

    account_type: AccountType | None = None


class RoleOwnClientResourceResponse(ApiSchema):
    """角色拥有的客户端资源响应结构。"""

    id: str
    modules: list[ResourceGrantModuleOption] = Field(default_factory=list)
    grant_info_list: list[RoleResourceGrantInfo] = Field(default_factory=list)


class RoleGrantClientResourceRequest(ApiSchema):
    """给角色授权客户端资源的请求（account_type 缺省按 ADMIN，对齐 hei-boot）。"""

    id: str = Field(min_length=1, max_length=64)
    account_type: AccountType = AccountType.ADMIN
    grant_info_list: list[RoleResourceGrantInfo] = Field(default_factory=list)


class RoleOwnUserResponse(ApiSchema):
    """角色拥有的用户响应结构。"""

    id: str
    users: list[SysAccountSchema] = Field(default_factory=list)
    account_ids: list[str] = Field(default_factory=list)


class RoleGrantUserRequest(ApiSchema):
    """给角色授权用户的请求。"""

    id: str = Field(min_length=1, max_length=64)
    account_ids: list[str] = Field(default_factory=list)
