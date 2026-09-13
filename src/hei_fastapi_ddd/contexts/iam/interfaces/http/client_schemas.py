""" Author: Charlie

客户端模块/资源 Schema：模块与资源的请求、分页查询及响应结构。
"""

from datetime import datetime

from pydantic import Field, field_serializer

from hei_fastapi_ddd.shared.config.enums import AccountType, DataScope, StatusEnum
from hei_fastapi_ddd.shared.web.pagination import PageQuery
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool, WireInt
from hei_fastapi_ddd.contexts.iam.domain.enums import ResourceType


class ClientModuleCreateRequest(ApiSchema):
    """创建客户端模块请求。"""

    name: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64)
    account_type: AccountType = AccountType.ADMIN
    icon: str | None = Field(default=None, max_length=255)
    color: str | None = Field(default=None, max_length=32)
    sort: WireInt = 99
    status: StatusEnum = StatusEnum.ENABLED
    description: str | None = None
    extra: dict = Field(default_factory=dict)


class ClientModuleUpdateRequest(ClientModuleCreateRequest):
    """更新客户端模块请求。"""

    id: str = Field(min_length=1, max_length=64)


class ClientModuleAdminPageQuery(PageQuery):
    """客户端模块管理端分页查询条件。"""

    name: str | None = Field(default=None, max_length=64)
    code: str | None = Field(default=None, max_length=64)
    account_type: AccountType | None = None
    status: str | None = Field(default=None, max_length=32)


class ClientModuleSelectorQuery(ApiSchema):
    """客户端模块下拉查询条件。"""

    account_type: AccountType | None = None


class SysClientModuleSchema(ApiSchema):
    """客户端模块响应结构。"""

    id: str
    name: str
    code: str
    account_type: AccountType
    icon: str | None = None
    color: str | None = None
    sort: WireInt
    status: str
    description: str | None = None
    extra: dict
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None

class ClientModuleSelectorOption(ApiSchema):
    """客户端模块下拉选项结构。"""

    id: str
    name: str
    code: str
    account_type: AccountType
    icon: str | None = None
    color: str | None = None
    sort: WireInt


class ClientResourceCreateRequest(ApiSchema):
    """创建客户端资源请求。"""

    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    resource_type: ResourceType
    parent_id: str | None = Field(default=None, max_length=64)
    module_id: str | None = Field(default=None, max_length=64)
    path: str | None = Field(default=None, max_length=255)
    component: str | None = Field(default=None, max_length=255)
    redirect: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=255)
    color: str | None = Field(default=None, max_length=32)
    href: str | None = Field(default=None, max_length=255)
    sort: WireInt = 99
    is_visible: WireBool = True
    is_cache: WireBool = False
    is_affix: WireBool = False
    status: StatusEnum = StatusEnum.ENABLED
    description: str | None = None
    layout: str | None = Field(default=None, max_length=255)
    extra: dict = Field(default_factory=dict)


class ClientResourceUpdateRequest(ClientResourceCreateRequest):
    """更新客户端资源请求。"""

    id: str = Field(min_length=1, max_length=64)


class ClientResourceAdminPageQuery(PageQuery):
    """客户端资源管理端分页查询条件。"""

    code: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=64)
    resource_type: ResourceType | None = None
    module_id: str | None = Field(default=None, max_length=64)
    parent_id: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=32)


class ClientResourceTreeQuery(ApiSchema):
    """客户端资源树查询条件。"""

    module_id: str | None = Field(default=None, max_length=64)
    account_type: AccountType | None = None


class SysClientResourceSchema(ApiSchema):
    """客户端资源响应结构。"""

    id: str
    parent_id: str | None = None
    code: str
    name: str
    resource_type: ResourceType
    module_id: str | None = None
    module_id_name: str | None = None
    account_type: AccountType | None = None
    path: str | None = None
    component: str | None = None
    redirect: str | None = None
    icon: str | None = None
    color: str | None = None
    href: str | None = None
    sort: WireInt
    is_visible: WireBool
    is_cache: WireBool
    is_affix: WireBool
    status: str
    description: str | None = None
    layout: str | None = None
    extra: dict
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None
    children: list["SysClientResourceSchema"] = Field(default_factory=list)


class ClientResourceTreeNode(SysClientResourceSchema):
    """客户端资源树节点结构（空 children 不出现在 JSON 中，对齐 hei-boot NON_EMPTY）。"""

    weight: WireInt | None = None
    parent_id_name: str | None = None
    children: list["ClientResourceTreeNode"] | None = Field(default=None)

    @field_serializer("children", when_used="json")
    def _omit_empty_children(self, value: list["ClientResourceTreeNode"] | None):
        """空列表序列化为 None，使叶子节点省略 children 键。"""
        return value or None


class ClientResourcePermissionBindRequest(ApiSchema):
    """客户端资源权限绑定请求。"""

    resource_id: str
    permission_key: str
    account_type: AccountType = AccountType.ADMIN
    data_scope: DataScope = DataScope.SELF
    custom_scope_dept_ids: list[str] = Field(default_factory=list)
    sort: WireInt = 99
    description: str | None = None


class SysClientResourcePermissionRelSchema(ApiSchema):
    """客户端资源-权限关系响应结构。"""

    id: str
    resource_id: str
    permission_key: str
    data_scope: DataScope
    custom_scope_dept_ids: list[str]
    sort: WireInt
    status: str
    description: str | None = None
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None