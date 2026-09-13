""" Author: Charlie

意见反馈枚举。
"""

from enum import StrEnum


class FeedbackStatus(StrEnum):
    """反馈处理状态。"""

    PENDING = "PENDING"  # 待处理
    REVIEWED = "REVIEWED"  # 已受理
    RESOLVED = "RESOLVED"  # 已解决
    CLOSED = "CLOSED"  # 已关闭
