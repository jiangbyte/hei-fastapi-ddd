""" Author: Charlie

通知/公告枚举：类型、状态与目标范围。
"""

from enum import StrEnum


class NoticeKind(StrEnum):
    """消息类型：通知或公告。"""

    NOTIFICATION = "NOTIFICATION"  # 通知
    ANNOUNCEMENT = "ANNOUNCEMENT"  # 公告


class NoticeStatus(StrEnum):
    """消息状态。"""

    DRAFT = "DRAFT"  # 草稿
    PUBLISHED = "PUBLISHED"  # 已发布
    REVOKED = "REVOKED"  # 已撤回


class TargetScope(StrEnum):
    """消息目标范围。"""

    ALL = "ALL"  # 全部
    ACCOUNT_TYPE = "ACCOUNT_TYPE"  # 按账户类型
    SPECIFIC = "SPECIFIC"  # 指定用户
