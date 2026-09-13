""" Author: Charlie

IAM 领域枚举：定义角色作用域、资源类型、授权模式以及关系主体/目标等类型常量。
"""

from enum import StrEnum


class RoleScopeType(StrEnum):
    """角色作用域类型。"""

    PLATFORM = "PLATFORM"  # 平台级
    DEPT = "DEPT"  # 部门级


class ResourceType(StrEnum):
    """资源类型。"""

    CATALOG = "CATALOG"  # 目录
    MENU = "MENU"  # 菜单
    PAGE = "PAGE"  # 页面
    BUTTON = "BUTTON"  # 按钮
    ACTION = "ACTION"  # 操作
    API_GROUP = "API_GROUP"  # API 组


class GrantSubjectType(StrEnum):
    """授权对象（主体）类型。"""

    ROLE = "ROLE"  # 角色
    ACCOUNT = "ACCOUNT"  # 账户
    GROUP = "GROUP"  # 组


class GrantMode(StrEnum):
    """授权模式。"""

    DIRECT = "DIRECT"  # 直接授权
    CASCADE = "CASCADE"  # 级联授权


class IamRelationType(StrEnum):
    """IAM 通用关系类型。"""

    ACCOUNT_ROLE = "ACCOUNT_ROLE"  # 账户-角色
    ACCOUNT_DEPT = "ACCOUNT_DEPT"  # 账户-部门
    ACCOUNT_GROUP = "ACCOUNT_GROUP"  # 账户-组
    GROUP_ROLE = "GROUP_ROLE"  # 组-角色
    SUBJECT_RESOURCE_GRANT = "SUBJECT_RESOURCE_GRANT"  # 主体-资源授权
    RESOURCE_PERMISSION = "RESOURCE_PERMISSION"  # 资源-权限
    SUBJECT_CLIENT_RESOURCE_GRANT = "SUBJECT_CLIENT_RESOURCE_GRANT"  # 主体-客户端资源授权
    CLIENT_RESOURCE_PERMISSION = "CLIENT_RESOURCE_PERMISSION"  # 客户端资源-权限


class IamRelationSubjectType(StrEnum):
    """IAM 通用关系主体类型。"""

    ACCOUNT = "ACCOUNT"  # 账户
    GROUP = "GROUP"  # 组
    ROLE = "ROLE"  # 角色
    RESOURCE = "RESOURCE"  # 资源
    CLIENT_RESOURCE = "CLIENT_RESOURCE"  # 客户端资源


class IamRelationTargetType(StrEnum):
    """IAM 通用关系目标类型。"""

    ACCOUNT = "ACCOUNT"  # 账户
    GROUP = "GROUP"  # 组
    ROLE = "ROLE"  # 角色
    DEPT = "DEPT"  # 部门
    RESOURCE = "RESOURCE"  # 资源
    CLIENT_RESOURCE = "CLIENT_RESOURCE"  # 客户端资源
    PERMISSION = "PERMISSION"  # 权限


class AccountIdentityType(StrEnum):
    """账户登录标识类型。"""

    ACCOUNT = "ACCOUNT"  # 登录账号
    EMAIL = "EMAIL"  # 邮箱登录标识
    PHONE = "PHONE"  # 手机号登录标识


class AccountIdentityBindStatus(StrEnum):
    """账户登录标识绑定状态。"""

    BOUND = "BOUND"  # 已绑定
    UNBOUND = "UNBOUND"  # 未绑定
