""" Author: Charlie

IAM 公共 Schema：账户、角色、资源授权与权限注册表等跨子模块复用的响应结构。
"""

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType, DataScope
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityBindStatus, AccountIdentityType
from hei_fastapi_ddd.contexts.profile.interfaces.http.identity_schemas import IdentityStatusResponse


class AccountIdentitySchema(ApiSchema):
    """账户登录标识响应结构。"""

    id: str | None = None
    account_id: str | None = None
    identity_type: AccountIdentityType
    identifier: str = Field(min_length=1, max_length=128)
    verified: WireBool = False
    is_primary: WireBool = False
    bind_status: AccountIdentityBindStatus = AccountIdentityBindStatus.BOUND
    created_at: datetime | None = None
    created_by: str | None = None
    updated_at: datetime | None = None
    updated_by: str | None = None


class SysAccountListSchema(ApiSchema):
    """账号分页列表响应：仅 sys_account 与 profile 展示字段。"""

    id: str
    account: str
    account_type: AccountType
    account_status: AccountStatusEnum
    nickname: str | None = None
    avatar: str | None = None
    phone: str | None = None
    email: str | None = None
    remark: str | None = None
    latest_login_time: datetime | None = None
    updated_at: datetime = Field(examples=["2026-06-18T12:00:00Z"])


class SysAccountSchema(ApiSchema):
    """系统账户响应结构，聚合账户主体、登录标识与登录轨迹信息。"""

    id: str
    account: str
    account_type: AccountType
    account_status: AccountStatusEnum
    name: str | None = None
    nickname: str | None = None
    avatar: str | None = None
    signature: str | None = None
    phone: str | None = None
    email: str | None = None
    email_login_enabled: WireBool = False
    phone_login_enabled: WireBool = False
    email_identity: str | None = None
    phone_identity: str | None = None
    email_identity_verified: WireBool = False
    phone_identity_verified: WireBool = False
    email_identity_bind_status: AccountIdentityBindStatus | None = None
    phone_identity_bind_status: AccountIdentityBindStatus | None = None
    identities: list[AccountIdentitySchema] = Field(default_factory=list)
    oauth_bindings: list["AccountOauthBindingSchema"] = Field(default_factory=list)
    identity_status: IdentityStatusResponse | None = None
    bio: str | None = None
    level: str | None = None
    remark: str | None = None
    cancelled_at: datetime | None = Field(default=None, examples=["2026-06-18T12:00:00Z"])
    cancelled_by: str | None = None
    cancel_reason: str | None = None
    last_login_ip: str | None = None
    last_login_address: str | None = None
    last_login_time: datetime | None = None
    last_login_device: str | None = None
    latest_login_ip: str | None = None
    latest_login_address: str | None = None
    latest_login_time: datetime | None = None
    latest_login_device: str | None = None
    created_at: datetime = Field(examples=["2026-06-18T12:00:00Z"])
    created_by: str | None = None
    updated_at: datetime = Field(examples=["2026-06-18T12:00:00Z"])
    updated_by: str | None = None


class AccountOauthBindingSchema(ApiSchema):
    """账户三方登录绑定项（对齐 hei-boot AccountOauthBindingResult）。"""

    id: str
    provider: str
    open_id: str
    union_id: str | None = None
    nickname: str | None = None
    avatar: str | None = None
    bound_at: datetime | None = None


class RoleOption(ApiSchema):
    """角色下拉选项结构。"""

    id: str
    code: str
    name: str
    status: str


class ResourcePermissionOption(ApiSchema):
    """资源权限挂载项结构。"""

    id: str
    permission_key: str
    title: str
    data_scope: DataScope = DataScope.SELF


class ResourceGrantMenuOption(ApiSchema):
    """资源授权菜单项结构。"""

    id: str
    module_id: str
    parent_id: str | None = None
    parent_id_name: str
    title: str
    button: list[ResourcePermissionOption] = Field(default_factory=list)


class ResourceGrantModuleOption(ApiSchema):
    """资源授权模块分组结构。"""

    id: str
    title: str
    menu: list[ResourceGrantMenuOption] = Field(default_factory=list)


class PermissionRegistryItem(ApiSchema):
    """权限注册表条目结构（module_code/resource_code/action 由权限码按 : 拆分派生）。"""

    permission_key: str
    name: str
    module_code: str | None = None
    resource_code: str | None = None
    action: str | None = None
    method: str | None = None
    path: str | None = None
