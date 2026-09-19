""" Author: Charlie

账户组 Schema：账户组创建/更新/分页查询及授权相关请求与响应结构。
"""

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.contexts.iam.api.iam_schemas import (
    ResourceGrantModuleOption,
    SysAccountSchema,
)
from hei_fastapi_ddd.contexts.iam.api.role_schemas import SysRoleSchema
from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum
from hei_fastapi_ddd.shared.schema.base import ApiSchema, IdQuery
from hei_fastapi_ddd.shared.web.pagination import PageQuery


class GroupCreateRequest(ApiSchema):
    """创建账户组请求。"""

    name: str = Field(min_length=1, max_length=64)
    owner_dept_id: str | None = Field(default=None, max_length=64)
    description: str | None = None
    status: StatusEnum = StatusEnum.ENABLED
    extra: dict = Field(default_factory=dict)


class GroupUpdateRequest(GroupCreateRequest):
    """更新账户组请求。"""

    id: str = Field(min_length=1, max_length=64)


class GroupAdminPageQuery(PageQuery):
    """账户组管理端分页查询条件。"""

    name: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=32)


class SysGroupSchema(ApiSchema):
    """账户组响应结构。"""

    id: str
    name: str
    owner_dept_id: str | None = None
    description: str | None = None
    status: str
    extra: dict
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None

class GroupRoleAssignRequest(ApiSchema):
    """为账户组追加单个角色的请求。"""

    group_id: str
    role_id: str
    account_type: AccountType


class SysGroupRoleRelSchema(ApiSchema):
    """账户组-角色关系响应结构。"""

    id: str
    group_id: str
    role_id: str
    account_type: str
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None


class GroupResourceGrantInfo(ApiSchema):
    """账户组资源授权项结构。"""

    resource_id: str = Field(min_length=1, max_length=64)
    permission_keys: list[str] = Field(default_factory=list)


class GroupOwnUserResponse(ApiSchema):
    """账户组拥有的成员响应结构。"""

    id: str
    users: list[SysAccountSchema] = Field(default_factory=list)
    account_ids: list[str] = Field(default_factory=list)


class GroupGrantUserRequest(ApiSchema):
    """给账户组授权成员的请求。"""

    id: str = Field(min_length=1, max_length=64)
    account_ids: list[str] = Field(default_factory=list)


class GroupOwnRoleQuery(IdQuery):
    """账户组角色查询条件（附带账户体系，缺省不过滤）。"""

    account_type: AccountType | None = None


class GroupOwnRoleResponse(ApiSchema):
    """账户组拥有的角色响应结构（roles 为完整角色实体，对齐 hei-boot）。"""

    id: str
    roles: list[SysRoleSchema] = Field(default_factory=list)
    role_ids: list[str] = Field(default_factory=list)


class GroupGrantRoleRequest(ApiSchema):
    """给账户组授权角色的请求（account_type 缺省按 ADMIN，对齐 hei-boot）。"""

    id: str = Field(min_length=1, max_length=64)
    account_type: AccountType = AccountType.ADMIN
    role_ids: list[str] = Field(default_factory=list)


class GroupOwnResourceQuery(IdQuery):
    """账户组资源查询条件（附带账户体系，缺省不过滤）。"""

    account_type: AccountType | None = None


class GroupOwnResourceResponse(ApiSchema):
    """账户组拥有的资源响应结构。"""

    id: str
    modules: list[ResourceGrantModuleOption] = Field(default_factory=list)
    grant_info_list: list[GroupResourceGrantInfo] = Field(default_factory=list)


class GroupGrantResourceRequest(ApiSchema):
    """给账户组授权资源的请求（account_type 缺省按 ADMIN，对齐 hei-boot）。"""

    id: str = Field(min_length=1, max_length=64)
    account_type: AccountType = AccountType.ADMIN
    grant_info_list: list[GroupResourceGrantInfo] = Field(default_factory=list)


class GroupOwnClientResourceQuery(IdQuery):
    """账户组客户端资源查询条件（附带账户体系，缺省不过滤）。"""

    account_type: AccountType | None = None


class GroupOwnClientResourceResponse(ApiSchema):
    """账户组拥有的客户端资源响应结构。"""

    id: str
    modules: list[ResourceGrantModuleOption] = Field(default_factory=list)
    grant_info_list: list[GroupResourceGrantInfo] = Field(default_factory=list)


class GroupGrantClientResourceRequest(ApiSchema):
    """给账户组授权客户端资源的请求（account_type 缺省按 ADMIN，对齐 hei-boot）。"""

    id: str = Field(min_length=1, max_length=64)
    account_type: AccountType = AccountType.ADMIN
    grant_info_list: list[GroupResourceGrantInfo] = Field(default_factory=list)
