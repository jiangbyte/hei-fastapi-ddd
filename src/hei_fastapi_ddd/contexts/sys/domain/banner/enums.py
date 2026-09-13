""" Author: Charlie

展示图模块枚举定义，值与 sys_dict 字典条目一致（大写+下划线体系）。
"""
from enum import StrEnum


class BannerCategory(StrEnum):
    """展示图分类，对应 BANNER_CATEGORY 字典组子项 value（可扩展，接口以 str 为准）。"""

    HOME = "HOME"
    LOGIN = "LOGIN"
    WORKPLACE = "WORKPLACE"
    NOTICE = "NOTICE"
    ADMIN_DASHBOARD = "ADMIN_DASHBOARD"
    SYSTEM_UPGRADE = "SYSTEM_UPGRADE"


class BannerType(StrEnum):
    """展示图类型，对应 BANNER_TYPE 字典组子项 value（可扩展，接口以 str 为准）。"""

    CAROUSEL = "CAROUSEL"
    HERO = "HERO"
    NOTICE = "NOTICE"
    CARD = "CARD"
    POPUP = "POPUP"
    SIDEBAR = "SIDEBAR"


class BannerPosition(StrEnum):
    """展示图显示位置，对应 BANNER_POSITION 字典组子项 value（可扩展，接口以 str 为准）。"""

    HOME_TOP = "HOME_TOP"
    HOME_MIDDLE = "HOME_MIDDLE"
    HOME_BOTTOM = "HOME_BOTTOM"
    LOGIN_SIDE = "LOGIN_SIDE"
    WORKPLACE_TOP = "WORKPLACE_TOP"
    NOTICE_AREA = "NOTICE_AREA"
    ADMIN_TOP = "ADMIN_TOP"
    ADMIN_SIDEBAR = "ADMIN_SIDEBAR"


class BannerLinkType(StrEnum):
    """展示图链接类型，对应 BANNER_LINK_TYPE 字典组子项 value。"""

    URL = "URL"
    ROUTE = "ROUTE"
    NONE = "NONE"
