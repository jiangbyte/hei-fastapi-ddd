""" Author: Charlie

账户 Schema：账户创建/更新/分页查询以及角色/组/部门/资源授权的请求与响应结构。
"""

from datetime import datetime

from pydantic import Field, field_validator

from hei_fastapi_ddd.contexts.iam.api.group_schemas import SysGroupSchema
from hei_fastapi_ddd.contexts.iam.api.iam_schemas import (
    AccountIdentitySchema as AccountIdentitySchema,
)
from hei_fastapi_ddd.contexts.iam.api.iam_schemas import (
    ResourceGrantModuleOption,
)
from hei_fastapi_ddd.contexts.iam.api.iam_schemas import (
    SysAccountListSchema as SysAccountListSchema,
)
from hei_fastapi_ddd.contexts.iam.api.iam_schemas import (
    SysAccountSchema as SysAccountSchema,
)
from hei_fastapi_ddd.contexts.iam.api.role_schemas import SysRoleSchema
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityBindStatus, AccountIdentityType
from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool
from hei_fastapi_ddd.shared.security.account_login import require_account_login
from hei_fastapi_ddd.shared.web.pagination import PageQuery


class AccountIdentityUpsertPayload(ApiSchema):
    """账户登录标识的新增/更新载荷。"""

    account_id: str
    identity_type: AccountIdentityType
    identifier: str = Field(min_length=1, max_length=128)
    verified: WireBool = False
    is_primary: WireBool = False
    bind_status: AccountIdentityBindStatus = AccountIdentityBindStatus.BOUND


class AccountUpdateLoginIdentityRequest(ApiSchema):
    """更新账户邮箱/手机号登录身份请求。"""

    id: str = Field(min_length=1, max_length=64)
    email_login_enabled: WireBool = False
    email: str | None = None
    phone_login_enabled: WireBool = False
    phone: str | None = None


class AccountCreateRequest(ApiSchema):
    """创建账户请求。"""

    account: str = Field(min_length=3, max_length=64)

    @field_validator("account")
    @classmethod
    def validate_account(cls, value: str) -> str:
        return require_account_login(value)

    password: str = Field(min_length=1, max_length=512)
    password_key_id: str | None = Field(default=None, max_length=64)
    account_type: AccountType
    account_status: AccountStatusEnum = AccountStatusEnum.ENABLED
    nickname: str | None = Field(default=None, max_length=64)
    avatar: str | None = None
    signature: str | None = None
    phone: str | None = None
    email: str | None = None
    remark: str | None = None


class AccountUpdateRequest(ApiSchema):
    """更新账户请求，密码为空时保持不变。"""

    id: str = Field(min_length=1, max_length=64)
    account: str = Field(min_length=3, max_length=64)

    @field_validator("account")
    @classmethod
    def validate_account(cls, value: str) -> str:
        return require_account_login(value)

    password: str | None = Field(default=None, min_length=1, max_length=512)
    password_key_id: str | None = Field(default=None, max_length=64)
    account_type: AccountType
    account_status: AccountStatusEnum = AccountStatusEnum.ENABLED
    nickname: str | None = Field(default=None, max_length=64)
    avatar: str | None = None
    signature: str | None = None
    phone: str | None = None
    email: str | None = None
    remark: str | None = None


class AccountCancelPayload(ApiSchema):
    """注销账户请求。"""

    id: str = Field(min_length=1, max_length=64)
    cancel_reason: str | None = None


class AccountAdminPageQuery(PageQuery):
    """账户管理端分页查询条件。"""

    account: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=128)
    account_type: AccountType | None = None
    account_status: AccountStatusEnum | None = None


class AccountRoleAssignRequest(ApiSchema):
    """为账户追加单个角色的请求。"""

    account_id: str
    role_id: str


class AccountGroupAssignRequest(ApiSchema):
    """为账户追加单个账户组的请求。"""

    account_id: str
    group_id: str


class AccountDeptAssignRequest(ApiSchema):
    """为账户追加单个部门的请求。"""

    account_id: str
    dept_id: str
    is_primary: WireBool = False


class AccountGroupOption(ApiSchema):
    """账户组下拉选项结构。"""

    id: str
    name: str
    status: str


class AccountDeptGrantInfo(ApiSchema):
    """账户部门授权项结构。"""

    dept_id: str
    is_primary: WireBool = False


class AccountResourceGrantInfo(ApiSchema):
    """账户资源授权项结构。"""

    resource_id: str = Field(min_length=1, max_length=64)
    permission_keys: list[str] = Field(default_factory=list)


class SysAccountRoleRelSchema(ApiSchema):
    """账户-角色关系响应结构。"""

    id: str
    account_id: str
    role_id: str
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None


class SysAccountGroupRelSchema(ApiSchema):
    """账户-账户组关系响应结构。"""

    id: str
    account_id: str
    group_id: str
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None


class SysAccountDeptRelSchema(ApiSchema):
    """账户-部门关系响应结构。"""

    id: str
    account_id: str
    dept_id: str
    is_primary: WireBool
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None


class AccountOwnResourceResponse(ApiSchema):
    """账户拥有的资源授权响应结构。"""

    id: str
    modules: list[ResourceGrantModuleOption] = Field(default_factory=list)
    grant_info_list: list[AccountResourceGrantInfo] = Field(default_factory=list)


class AccountGrantResourceRequest(ApiSchema):
    """给账户授权资源的请求。"""

    id: str = Field(min_length=1, max_length=64)
    grant_info_list: list[AccountResourceGrantInfo] = Field(default_factory=list)


class AccountOwnClientResourceResponse(ApiSchema):
    """账户拥有的客户端资源授权响应结构。"""

    id: str
    modules: list[ResourceGrantModuleOption] = Field(default_factory=list)
    grant_info_list: list[AccountResourceGrantInfo] = Field(default_factory=list)


class AccountGrantClientResourceRequest(ApiSchema):
    """给账户授权客户端资源的请求。"""

    id: str = Field(min_length=1, max_length=64)
    grant_info_list: list[AccountResourceGrantInfo] = Field(default_factory=list)


class AccountOwnRoleResponse(ApiSchema):
    """账户拥有的角色授权响应结构（roles 为完整角色实体，对齐 hei-boot）。"""

    id: str
    roles: list[SysRoleSchema] = Field(default_factory=list)
    role_ids: list[str] = Field(default_factory=list)


class AccountGrantRoleRequest(ApiSchema):
    """给账户授权角色的请求。"""

    id: str = Field(min_length=1, max_length=64)
    role_ids: list[str] = Field(default_factory=list)


class AccountOwnGroupResponse(ApiSchema):
    """账户拥有的账户组授权响应结构（groups 为完整组实体，对齐 hei-boot）。"""

    id: str
    groups: list[SysGroupSchema] = Field(default_factory=list)
    group_ids: list[str] = Field(default_factory=list)


class AccountGrantGroupRequest(ApiSchema):
    """给账户授权账户组的请求。"""

    id: str = Field(min_length=1, max_length=64)
    group_ids: list[str] = Field(default_factory=list)


class AccountOwnDeptResponse(ApiSchema):
    """账户拥有的部门授权响应结构。"""

    id: str
    grant_info_list: list[AccountDeptGrantInfo] = Field(default_factory=list)


class AccountGrantDeptRequest(ApiSchema):
    """给账户授权部门的请求。"""

    id: str = Field(min_length=1, max_length=64)
    grant_info_list: list[AccountDeptGrantInfo] = Field(default_factory=list)
