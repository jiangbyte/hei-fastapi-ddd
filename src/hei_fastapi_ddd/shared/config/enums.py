""" Author: Charlie

全局通用枚举：账户类型、数据范围、状态与存储服务商。

业务模块专用的枚举请放置在各模块自己的 enums.py 中。
"""

from enum import StrEnum


class AccountType(StrEnum):
    """账户类型身份（管理员、门户用户、未来商户/消费者等），不是展示端/渠道。

    扩展步骤：
    1. 在此增加枚举成员
    2. 前端 `@/constants/account` 的 ACCOUNT_TYPE 同步追加
    3. sys_config 种子按 `PREFIX_{TYPE}_FIELD` 补齐（注册/登录/密码等按账户类型配置）
       邮件/短信模板为全局 `MAIL_TEMPLATE_{SCENE}` / `SMS_TEMPLATE_{SCENE}`，不按类型拆分
    """

    ADMIN = "ADMIN"  # 管理员（管理后台）
    PORTAL = "PORTAL"  # 门户用户
    # MERCHANT = "MERCHANT"  # 商户（预留）
    # CONSUMER = "CONSUMER"  # 消费者（预留）


def account_type_url_segment(account_type: AccountType | str) -> str:
    """该账户类型默认 API 路径段：ADMIN -> admin。"""
    value = account_type.value if isinstance(account_type, AccountType) else str(account_type)
    return value.lower()


def account_config_key(prefix: str, account_type: AccountType | str, field: str) -> str:
    """按账户类型拼配置键：AUTH_REGISTER_PORTAL_ENABLED。扩展类型时键名自动对齐。"""
    value = account_type.value if isinstance(account_type, AccountType) else str(account_type)
    return f"{prefix}_{value}_{field}"


def account_types_with_profile() -> tuple[AccountType, ...]:
    """具备独立资料表的账户类型。"""
    return tuple(AccountType)


def account_types_with_auth_routes() -> tuple[AccountType, ...]:
    """具备 /v1/{segment}/... 认证与业务路由的账户类型。"""
    return tuple(AccountType)


class DataScope(StrEnum):
    """
    数据范围
    """

    ALL = "ALL"  # 全部
    DEPT_AND_CHILD = "DEPT_AND_CHILD"  # 部门及子部门
    DEPT = "DEPT"  # 部门
    SELF = "SELF"  # 本人
    CUSTOM = "CUSTOM"  # 自定义


class StatusEnum(StrEnum):
    """
    状态
    """

    ENABLED = "ENABLED"  # 启用
    DISABLED = "DISABLED"  # 禁用


class AccountStatusEnum(StrEnum):
    """
    账户状态
    """

    ENABLED = "ENABLED"  # 启用
    DISABLED = "DISABLED"  # 禁用
    CANCELLED = "CANCELLED"  # 注销


class SysBizCategory(StrEnum):
    """
    系统/业务分类
    """

    SYS = "SYS"  # 系统
    BIZ = "BIZ"  # 业务


class StorageProvider(StrEnum):
    """
    文件存储服务商（仅对象存储，对齐 hei-boot）
    """

    OSS = "oss"  # 阿里云 OSS
    S3 = "s3"  # 腾讯云 COS（S3 兼容）
    MINIO = "minio"  # MinIO
    RUSTFS = "rustfs"  # RustFS（S3 兼容，path-style）
