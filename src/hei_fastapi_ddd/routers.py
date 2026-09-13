""" Author: Charlie

API 路由装配：显式挂载全部限界上下文路由（对齐 hei-fastapi explicit deps）。

完整路径写在各路由装饰器上（``/v1/admin/...``），这里统一挂 ``/api`` 前缀并保留
OpenAPI tags（admin / portal / internal / public）。
"""

from __future__ import annotations

from functools import cache

from fastapi import APIRouter

from hei_fastapi_ddd.contexts.auth.interfaces.http.auth_router import (
    admin_router as auth_admin_router,
)
from hei_fastapi_ddd.contexts.auth.interfaces.http.auth_router import (
    portal_router as auth_portal_router,
)
from hei_fastapi_ddd.contexts.auth.interfaces.http.oauth_router import (
    admin_router as oauth_admin_router,
)
from hei_fastapi_ddd.contexts.auth.interfaces.http.oauth_router import (
    portal_router as oauth_portal_router,
)
from hei_fastapi_ddd.contexts.auth.interfaces.http.session_admin_router import (
    router as auth_session_admin_router,
)
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_activity_router import (
    router as cg_test_activity_router,
)
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_catalog_router import (
    router as cg_test_catalog_router,
)
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_knowledge_category_router import (
    router as cg_test_knowledge_router,
)
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_order_router import (
    router as cg_test_order_router,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.account_router import router as iam_account_router
from hei_fastapi_ddd.contexts.iam.interfaces.http.client_router import router as iam_client_router
from hei_fastapi_ddd.contexts.iam.interfaces.http.dept_router import router as iam_dept_router
from hei_fastapi_ddd.contexts.iam.interfaces.http.group_router import router as iam_group_router
from hei_fastapi_ddd.contexts.iam.interfaces.http.position_router import (
    router as iam_position_router,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.resource_portal_router import (
    router as iam_resource_portal_router,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.resource_router import (
    router as iam_resource_router,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.role_router import router as iam_role_router
from hei_fastapi_ddd.contexts.profile.interfaces.http.admin_router import (
    router as profile_admin_router,
)
from hei_fastapi_ddd.contexts.profile.interfaces.http.identity_router import (
    admin_manage_router as profile_identity_manage_router,
)
from hei_fastapi_ddd.contexts.profile.interfaces.http.identity_router import (
    admin_user_router as profile_identity_admin_router,
)
from hei_fastapi_ddd.contexts.profile.interfaces.http.identity_router import (
    portal_user_router as profile_identity_portal_router,
)
from hei_fastapi_ddd.contexts.profile.interfaces.http.portal_router import (
    router as profile_portal_router,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.audit_portal_router import (
    router as sys_audit_portal_router,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.audit_router import router as sys_audit_router
from hei_fastapi_ddd.contexts.sys.interfaces.http.banner_portal_router import (
    router as banner_portal_router,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.banner_router import router as banner_router
from hei_fastapi_ddd.contexts.sys.interfaces.http.codegen_router import router as sys_codegen_router
from hei_fastapi_ddd.contexts.sys.interfaces.http.config_router import router as sys_config_router
from hei_fastapi_ddd.contexts.sys.interfaces.http.dict_portal_router import (
    router as dict_portal_router,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.dict_router import router as sys_dict_router
from hei_fastapi_ddd.contexts.sys.interfaces.http.feedback_router import (
    admin_router as feedback_admin_router,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.feedback_router import (
    portal_router as feedback_portal_router,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.file_portal_router import (
    router as file_portal_router,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.file_router import router as sys_file_router
from hei_fastapi_ddd.contexts.sys.interfaces.http.health_router import (
    router as internal_health_router,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.job_router import router as sys_job_router
from hei_fastapi_ddd.contexts.sys.interfaces.http.notice_router import (
    admin_router as notice_admin_router,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.notice_router import (
    portal_router as notice_portal_router,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.public_router import router as sys_public_router
from hei_fastapi_ddd.contexts.sys.interfaces.http.weak_password_router import (
    router as weak_password_router,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.workspace_router import router as workspace_router
from hei_fastapi_ddd.shared.paths import API_ROOT_PREFIX
from hei_fastapi_ddd.shared.router import enable_response_exclude_none

# (tags, router) 挂载清单，顺序与历史注册顺序一致。
_ROUTERS: list[tuple[str, APIRouter]] = [
    ("admin", workspace_router),
    ("admin", auth_admin_router),
    ("portal", auth_portal_router),
    ("admin", auth_session_admin_router),
    ("admin", oauth_admin_router),
    ("portal", oauth_portal_router),
    ("admin", cg_test_activity_router),
    ("admin", cg_test_catalog_router),
    ("admin", cg_test_knowledge_router),
    ("admin", cg_test_order_router),
    ("admin", iam_account_router),
    ("admin", iam_client_router),
    ("admin", iam_dept_router),
    ("admin", iam_group_router),
    ("admin", iam_position_router),
    ("admin", iam_resource_router),
    ("portal", iam_resource_portal_router),
    ("admin", iam_role_router),
    ("internal", internal_health_router),
    ("admin", feedback_admin_router),
    ("portal", feedback_portal_router),
    ("admin", notice_admin_router),
    ("portal", notice_portal_router),
    ("admin", sys_audit_router),
    ("portal", sys_audit_portal_router),
    ("public", sys_public_router),
    ("admin", banner_router),
    ("portal", banner_portal_router),
    ("admin", sys_codegen_router),
    ("admin", sys_config_router),
    ("admin", sys_dict_router),
    ("portal", dict_portal_router),
    ("admin", sys_file_router),
    ("portal", file_portal_router),
    ("admin", sys_job_router),
    ("admin", weak_password_router),
    ("admin", profile_admin_router),
    ("admin", profile_identity_admin_router),
    ("admin", profile_identity_manage_router),
    ("portal", profile_identity_portal_router),
    ("portal", profile_portal_router),
]


@cache
def get_api_router() -> APIRouter:
    """构建并缓存 API 根路由。"""
    api_router = APIRouter()
    for tags, router in _ROUTERS:
        api_router.include_router(router, prefix=API_ROOT_PREFIX, tags=[tags])
    enable_response_exclude_none(api_router)
    return api_router
