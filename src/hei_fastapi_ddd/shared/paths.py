""" Author: Charlie

与路由装饰器约定对齐的路径常量（非“改一处升全库版本”）。

项目约定：全局挂 ``/api``（见 app/routers.py），完整路径写在装饰器上，例如
``/v1/admin/sys/positions/create``。升 API 版本需同步改装饰器（或全库替换 ``/v1/``）。

此处只放：
- ``API_ROOT_PREFIX``：路由挂载用
- ``api_version_glob_prefix``：白名单 fnmatch 用 ``/api/v*``，匹配时不绑死某一版
"""
from __future__ import annotations

# 路由挂载的全局 API 前缀。
API_ROOT_PREFIX = "/api"


def api_version_glob_prefix() -> str:
    """供 fnmatch 使用的版本通配前缀：/api/v*。"""
    return f"{API_ROOT_PREFIX}/v*"
