#!/usr/bin/env python3
"""将 hei-fastapi/app/modules 迁移到 hei-fastapi-ddd contexts 四层结构。

仅用于一次性迁移；不修改源项目。
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path("/home/charlie/Workspace/projects/mine/hei/hei-fastapi/app/modules")
DEST = Path("/home/charlie/Workspace/projects/mine/hei/hei-fastapi-ddd/src/hei_fastapi_ddd/contexts")

# 显式文件映射：相对 SRC → 相对 DEST
EXPLICIT: dict[str, str] = {
    # ---- sys/dict（占位，稍后由 deep DDD 覆盖）----
    "sys/dict/model.py": "sys/infrastructure/persistence/dict_po.py",
    "sys/dict/repository.py": "sys/infrastructure/persistence/dict_repository.py",
    "sys/dict/service.py": "sys/application/dict/dict_application_service.py",
    "sys/dict/schema.py": "sys/interfaces/http/dict_schemas.py",
    "sys/dict/router.py": "sys/interfaces/http/dict_router.py",
    "sys/dict/portal/router.py": "sys/interfaces/http/dict_portal_router.py",
    # ---- sys/audit specials ----
    "sys/audit/outbox.py": "sys/infrastructure/persistence/audit_outbox.py",
    "sys/audit/event_handler.py": "sys/infrastructure/audit_event_handler.py",
    "sys/audit/labels.py": "sys/infrastructure/audit_labels.py",
    "sys/audit/model.py": "sys/infrastructure/persistence/audit_po.py",
    "sys/audit/alert_model.py": "sys/infrastructure/persistence/audit_alert_po.py",
    "sys/audit/repository.py": "sys/infrastructure/persistence/audit_repository.py",
    "sys/audit/service.py": "sys/application/audit/audit_application_service.py",
    "sys/audit/schema.py": "sys/interfaces/http/audit_schemas.py",
    "sys/audit/router.py": "sys/interfaces/http/audit_router.py",
    "sys/audit/portal_router.py": "sys/interfaces/http/audit_portal_router.py",
    "sys/audit/alert.py": "sys/application/audit/alert.py",
    "sys/audit/analyzer.py": "sys/application/audit/analyzer.py",
    "sys/audit/support.py": "sys/application/audit/support.py",
    "sys/audit/tasks.py": "sys/application/audit/tasks.py",
    # ---- sys/job specials ----
    "sys/job/scheduler.py": "sys/infrastructure/job_scheduler.py",
    "sys/job/model.py": "sys/infrastructure/persistence/job_po.py",
    "sys/job/repository.py": "sys/infrastructure/persistence/job_repository.py",
    "sys/job/service.py": "sys/application/job/job_application_service.py",
    "sys/job/schema.py": "sys/interfaces/http/job_schemas.py",
    "sys/job/router.py": "sys/interfaces/http/job_router.py",
    "sys/job/cron.py": "sys/application/job/cron.py",
    "sys/job/execution.py": "sys/application/job/execution.py",
    "sys/job/registry.py": "sys/application/job/registry.py",
    "sys/job/sample.py": "sys/application/job/sample.py",
    "sys/job/tasks.py": "sys/application/job/tasks.py",
    # ---- sys/banner ----
    "sys/banner/model.py": "sys/infrastructure/persistence/banner_po.py",
    "sys/banner/repository.py": "sys/infrastructure/persistence/banner_repository.py",
    "sys/banner/service.py": "sys/application/banner/banner_application_service.py",
    "sys/banner/schema.py": "sys/interfaces/http/banner_schemas.py",
    "sys/banner/router.py": "sys/interfaces/http/banner_router.py",
    "sys/banner/portal/router.py": "sys/interfaces/http/banner_portal_router.py",
    "sys/banner/enums.py": "sys/domain/banner/enums.py",
    "sys/banner/tasks.py": "sys/application/banner/tasks.py",
    # ---- sys/codegen ----
    "sys/codegen/model.py": "sys/infrastructure/persistence/codegen_po.py",
    "sys/codegen/repository.py": "sys/infrastructure/persistence/codegen_repository.py",
    "sys/codegen/service.py": "sys/application/codegen/codegen_application_service.py",
    "sys/codegen/schema.py": "sys/interfaces/http/codegen_schemas.py",
    "sys/codegen/router.py": "sys/interfaces/http/codegen_router.py",
    "sys/codegen/apply.py": "sys/application/codegen/apply.py",
    "sys/codegen/paths.py": "sys/application/codegen/paths.py",
    "sys/codegen/templates.py": "sys/application/codegen/templates.py",
    # ---- sys/config ----
    "sys/config/repository.py": "sys/infrastructure/persistence/config_repository.py",
    "sys/config/service.py": "sys/application/config/config_application_service.py",
    "sys/config/schema.py": "sys/interfaces/http/config_schemas.py",
    "sys/config/router.py": "sys/interfaces/http/config_router.py",
    # ---- sys/feedback ----
    "sys/feedback/model.py": "sys/infrastructure/persistence/feedback_po.py",
    "sys/feedback/repository.py": "sys/infrastructure/persistence/feedback_repository.py",
    "sys/feedback/service.py": "sys/application/feedback/feedback_application_service.py",
    "sys/feedback/schema.py": "sys/interfaces/http/feedback_schemas.py",
    "sys/feedback/router.py": "sys/interfaces/http/feedback_router.py",
    "sys/feedback/enums.py": "sys/domain/feedback/enums.py",
    # ---- sys/file ----
    "sys/file/model.py": "sys/infrastructure/persistence/file_po.py",
    "sys/file/repository.py": "sys/infrastructure/persistence/file_repository.py",
    "sys/file/service.py": "sys/application/file/file_application_service.py",
    "sys/file/schema.py": "sys/interfaces/http/file_schemas.py",
    "sys/file/router.py": "sys/interfaces/http/file_router.py",
    "sys/file/portal/router.py": "sys/interfaces/http/file_portal_router.py",
    "sys/file/content_disposition.py": "sys/application/file/content_disposition.py",
    # ---- sys/notice ----
    "sys/notice/model.py": "sys/infrastructure/persistence/notice_po.py",
    "sys/notice/repository.py": "sys/infrastructure/persistence/notice_repository.py",
    "sys/notice/service.py": "sys/application/notice/notice_application_service.py",
    "sys/notice/schema.py": "sys/interfaces/http/notice_schemas.py",
    "sys/notice/router.py": "sys/interfaces/http/notice_router.py",
    "sys/notice/enums.py": "sys/domain/notice/enums.py",
    "sys/notice/target_scope.py": "sys/application/notice/target_scope.py",
    # ---- sys/public ----
    "sys/public/router.py": "sys/interfaces/http/public_router.py",
    "sys/public/site_footer.py": "sys/application/public/site_footer.py",
    # ---- sys/weak_password ----
    "sys/weak_password/repository.py": "sys/infrastructure/persistence/weak_password_repository.py",
    "sys/weak_password/service.py": "sys/application/weak_password/weak_password_application_service.py",
    "sys/weak_password/schema.py": "sys/interfaces/http/weak_password_schemas.py",
    "sys/weak_password/router.py": "sys/interfaces/http/weak_password_router.py",
    # ---- sys/workspace ----
    "sys/workspace/model.py": "sys/infrastructure/persistence/workspace_po.py",
    "sys/workspace/repository.py": "sys/infrastructure/persistence/workspace_repository.py",
    "sys/workspace/service.py": "sys/application/workspace/workspace_application_service.py",
    "sys/workspace/schema.py": "sys/interfaces/http/workspace_schemas.py",
    "sys/workspace/router.py": "sys/interfaces/http/workspace_router.py",
    # ---- internal → sys ----
    "internal/health/router.py": "sys/interfaces/http/health_router.py",
    # ---- iam/account ----
    "iam/account/model.py": "iam/infrastructure/persistence/account_po.py",
    "iam/account/repository.py": "iam/infrastructure/persistence/account_repository.py",
    "iam/account/service.py": "iam/application/account/account_application_service.py",
    "iam/account/query_service.py": "iam/application/account/query_service.py",
    "iam/account/schema.py": "iam/interfaces/http/account_schemas.py",
    "iam/account/router.py": "iam/interfaces/http/account_router.py",
    "iam/account/notify.py": "iam/application/account/notify.py",
    "iam/account/password_helper.py": "iam/application/account/password_helper.py",
    "iam/account/password_history.py": "iam/infrastructure/persistence/password_history_po.py",
    "iam/account/tasks.py": "iam/application/account/tasks.py",
    # ---- iam/client ----
    "iam/client/model.py": "iam/infrastructure/persistence/client_po.py",
    "iam/client/repository.py": "iam/infrastructure/persistence/client_repository.py",
    "iam/client/service.py": "iam/application/client/client_application_service.py",
    "iam/client/schema.py": "iam/interfaces/http/client_schemas.py",
    "iam/client/router.py": "iam/interfaces/http/client_router.py",
    # ---- iam/dept ----
    "iam/dept/model.py": "iam/infrastructure/persistence/dept_po.py",
    "iam/dept/repository.py": "iam/infrastructure/persistence/dept_repository.py",
    "iam/dept/service.py": "iam/application/dept/dept_application_service.py",
    "iam/dept/schema.py": "iam/interfaces/http/dept_schemas.py",
    "iam/dept/router.py": "iam/interfaces/http/dept_router.py",
    "iam/dept/resolver.py": "iam/infrastructure/dept_resolver.py",
    # ---- iam/group ----
    "iam/group/model.py": "iam/infrastructure/persistence/group_po.py",
    "iam/group/repository.py": "iam/infrastructure/persistence/group_repository.py",
    "iam/group/service.py": "iam/application/group/group_application_service.py",
    "iam/group/schema.py": "iam/interfaces/http/group_schemas.py",
    "iam/group/router.py": "iam/interfaces/http/group_router.py",
    # ---- iam/position ----
    "iam/position/model.py": "iam/infrastructure/persistence/position_po.py",
    "iam/position/repository.py": "iam/infrastructure/persistence/position_repository.py",
    "iam/position/service.py": "iam/application/position/position_application_service.py",
    "iam/position/schema.py": "iam/interfaces/http/position_schemas.py",
    "iam/position/router.py": "iam/interfaces/http/position_router.py",
    # ---- iam/resource ----
    "iam/resource/model.py": "iam/infrastructure/persistence/resource_po.py",
    "iam/resource/repository.py": "iam/infrastructure/persistence/resource_repository.py",
    "iam/resource/service.py": "iam/application/resource/resource_application_service.py",
    "iam/resource/schema.py": "iam/interfaces/http/resource_schemas.py",
    "iam/resource/router.py": "iam/interfaces/http/resource_router.py",
    "iam/resource/portal/router.py": "iam/interfaces/http/resource_portal_router.py",
    # ---- iam/role ----
    "iam/role/model.py": "iam/infrastructure/persistence/role_po.py",
    "iam/role/repository.py": "iam/infrastructure/persistence/role_repository.py",
    "iam/role/service.py": "iam/application/role/role_application_service.py",
    "iam/role/schema.py": "iam/interfaces/http/role_schemas.py",
    "iam/role/router.py": "iam/interfaces/http/role_router.py",
    "iam/role/constants.py": "iam/domain/role/constants.py",
    # ---- iam/relation ----
    "iam/relation/model.py": "iam/infrastructure/persistence/relation_po.py",
    "iam/relation/repository.py": "iam/infrastructure/persistence/relation_repository.py",
    # ---- iam helpers ----
    "iam/enums.py": "iam/domain/enums.py",
    "iam/schema.py": "iam/interfaces/http/iam_schemas.py",
    "iam/reference_guard.py": "iam/application/reference_guard.py",
    "iam/support/audit.py": "iam/application/support/audit.py",
    # ---- profile ----
    "profile/admin/model.py": "profile/infrastructure/persistence/admin_po.py",
    "profile/admin/repository.py": "profile/infrastructure/persistence/admin_repository.py",
    "profile/admin/service.py": "profile/application/admin/admin_application_service.py",
    "profile/admin/schema.py": "profile/interfaces/http/admin_schemas.py",
    "profile/admin/router.py": "profile/interfaces/http/admin_router.py",
    "profile/portal/model.py": "profile/infrastructure/persistence/portal_po.py",
    "profile/portal/repository.py": "profile/infrastructure/persistence/portal_repository.py",
    "profile/portal/service.py": "profile/application/portal/portal_application_service.py",
    "profile/portal/schema.py": "profile/interfaces/http/portal_schemas.py",
    "profile/portal/router.py": "profile/interfaces/http/portal_router.py",
    "profile/identity/model.py": "profile/infrastructure/persistence/identity_po.py",
    "profile/identity/repository.py": "profile/infrastructure/persistence/identity_repository.py",
    "profile/identity/service.py": "profile/application/identity/identity_application_service.py",
    "profile/identity/schema.py": "profile/interfaces/http/identity_schemas.py",
    "profile/identity/router.py": "profile/interfaces/http/identity_router.py",
    "profile/identity/crypto.py": "profile/application/identity/crypto.py",
    "profile/identity/enums.py": "profile/domain/identity/enums.py",
    "profile/identity/handlers.py": "profile/application/identity/handlers.py",
    "profile/identity/support.py": "profile/application/identity/support.py",
    "profile/identity/providers/base.py": "profile/infrastructure/identity_providers/base.py",
    "profile/identity/providers/mock.py": "profile/infrastructure/identity_providers/mock.py",
    "profile/identity/providers/registry.py": "profile/infrastructure/identity_providers/registry.py",
    "profile/identity/providers/third_party.py": "profile/infrastructure/identity_providers/third_party.py",
    "profile/schema.py": "profile/interfaces/http/profile_schemas.py",
    "profile/utils/profile.py": "profile/application/utils/profile.py",
    # ---- auth ----
    "auth/base.py": "auth/application/base.py",
    "auth/bind_service.py": "auth/application/bind_service.py",
    "auth/lifecycle_service.py": "auth/application/lifecycle_service.py",
    "auth/login_service.py": "auth/application/login_service.py",
    "auth/password_change.py": "auth/application/password_change.py",
    "auth/password_reset_service.py": "auth/application/password_reset_service.py",
    "auth/policy.py": "auth/domain/policy.py",
    "auth/protection.py": "auth/application/protection.py",
    "auth/register_service.py": "auth/application/register_service.py",
    "auth/service.py": "auth/application/auth_application_service.py",
    "auth/session_service.py": "auth/application/session_service.py",
    "auth/session_admin_service.py": "auth/application/session_admin_service.py",
    "auth/schema.py": "auth/interfaces/http/auth_schemas.py",
    "auth/session_schema.py": "auth/interfaces/http/session_schemas.py",
    "auth/router.py": "auth/interfaces/http/auth_router.py",
    "auth/session_admin_router.py": "auth/interfaces/http/session_admin_router.py",
    "auth/oauth/model.py": "auth/infrastructure/persistence/oauth_po.py",
    "auth/oauth/repository.py": "auth/infrastructure/persistence/oauth_repository.py",
    "auth/oauth/service.py": "auth/application/oauth/oauth_application_service.py",
    "auth/oauth/schema.py": "auth/interfaces/http/oauth_schemas.py",
    "auth/oauth/router.py": "auth/interfaces/http/oauth_router.py",
    "auth/oauth/client.py": "auth/infrastructure/oauth/client.py",
    "auth/oauth/provider.py": "auth/infrastructure/oauth/provider.py",
    "auth/oauth/stores.py": "auth/infrastructure/oauth/stores.py",
    # ---- biz ----
    "biz/cg_test_activity/model.py": "biz/infrastructure/persistence/cg_test_activity_po.py",
    "biz/cg_test_activity/repository.py": "biz/infrastructure/persistence/cg_test_activity_repository.py",
    "biz/cg_test_activity/service.py": "biz/application/cg_test_activity/cg_test_activity_application_service.py",
    "biz/cg_test_activity/schema.py": "biz/interfaces/http/cg_test_activity_schemas.py",
    "biz/cg_test_activity/router.py": "biz/interfaces/http/cg_test_activity_router.py",
    "biz/cg_test_catalog/model.py": "biz/infrastructure/persistence/cg_test_catalog_po.py",
    "biz/cg_test_catalog/repository.py": "biz/infrastructure/persistence/cg_test_catalog_repository.py",
    "biz/cg_test_catalog/service.py": "biz/application/cg_test_catalog/cg_test_catalog_application_service.py",
    "biz/cg_test_catalog/schema.py": "biz/interfaces/http/cg_test_catalog_schemas.py",
    "biz/cg_test_catalog/router.py": "biz/interfaces/http/cg_test_catalog_router.py",
    "biz/cg_test_knowledge_category/model.py": "biz/infrastructure/persistence/cg_test_knowledge_category_po.py",
    "biz/cg_test_knowledge_category/repository.py": "biz/infrastructure/persistence/cg_test_knowledge_category_repository.py",
    "biz/cg_test_knowledge_category/service.py": "biz/application/cg_test_knowledge_category/cg_test_knowledge_category_application_service.py",
    "biz/cg_test_knowledge_category/schema.py": "biz/interfaces/http/cg_test_knowledge_category_schemas.py",
    "biz/cg_test_knowledge_category/router.py": "biz/interfaces/http/cg_test_knowledge_category_router.py",
    "biz/cg_test_order/model.py": "biz/infrastructure/persistence/cg_test_order_po.py",
    "biz/cg_test_order/repository.py": "biz/infrastructure/persistence/cg_test_order_repository.py",
    "biz/cg_test_order/service.py": "biz/application/cg_test_order/cg_test_order_application_service.py",
    "biz/cg_test_order/schema.py": "biz/interfaces/http/cg_test_order_schemas.py",
    "biz/cg_test_order/router.py": "biz/interfaces/http/cg_test_order_router.py",
}

# 模块内导入路径重写（旧完整模块路径 → 新完整模块路径）
# 按最长匹配顺序；由 EXPLICIT 生成
MODULE_REWRITES: list[tuple[str, str]] = []


def _old_mod(rel: str) -> str:
    return "app.modules." + rel.replace("/", ".").removesuffix(".py")


def _new_mod(rel: str) -> str:
    return "hei_fastapi_ddd.contexts." + rel.replace("/", ".").removesuffix(".py")


def build_module_rewrites() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for old_rel, new_rel in EXPLICIT.items():
        pairs.append((_old_mod(old_rel), _new_mod(new_rel)))
    # 包级别兜底（无具体文件映射时）
    fallbacks = [
        ("app.modules.auth", "hei_fastapi_ddd.contexts.auth"),
        ("app.modules.iam", "hei_fastapi_ddd.contexts.iam"),
        ("app.modules.sys", "hei_fastapi_ddd.contexts.sys"),
        ("app.modules.profile", "hei_fastapi_ddd.contexts.profile"),
        ("app.modules.biz", "hei_fastapi_ddd.contexts.biz"),
        ("app.modules.internal", "hei_fastapi_ddd.contexts.sys.internal"),
    ]
    # 额外常见别名：旧 feature 包路径 → 新分层路径前缀
    aliases = [
        # dict
        ("app.modules.sys.dict.model", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.dict_po"),
        ("app.modules.sys.dict.repository", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.dict_repository"),
        ("app.modules.sys.dict.service", "hei_fastapi_ddd.contexts.sys.application.dict.dict_application_service"),
        ("app.modules.sys.dict.schema", "hei_fastapi_ddd.contexts.sys.interfaces.http.dict_schemas"),
        ("app.modules.sys.dict.portal.router", "hei_fastapi_ddd.contexts.sys.interfaces.http.dict_portal_router"),
        ("app.modules.sys.dict.router", "hei_fastapi_ddd.contexts.sys.interfaces.http.dict_router"),
        # account
        ("app.modules.iam.account.model", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po"),
        ("app.modules.iam.account.repository", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository"),
        ("app.modules.iam.account.service", "hei_fastapi_ddd.contexts.iam.application.account.account_application_service"),
        ("app.modules.iam.account.query_service", "hei_fastapi_ddd.contexts.iam.application.account.query_service"),
        ("app.modules.iam.account.schema", "hei_fastapi_ddd.contexts.iam.interfaces.http.account_schemas"),
        ("app.modules.iam.account.notify", "hei_fastapi_ddd.contexts.iam.application.account.notify"),
        ("app.modules.iam.account.password_helper", "hei_fastapi_ddd.contexts.iam.application.account.password_helper"),
        ("app.modules.iam.account.password_history", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.password_history_po"),
        ("app.modules.iam.account.tasks", "hei_fastapi_ddd.contexts.iam.application.account.tasks"),
        ("app.modules.iam.account.router", "hei_fastapi_ddd.contexts.iam.interfaces.http.account_router"),
        # auth services
        ("app.modules.auth.session_service", "hei_fastapi_ddd.contexts.auth.application.session_service"),
        ("app.modules.auth.service", "hei_fastapi_ddd.contexts.auth.application.auth_application_service"),
        ("app.modules.auth.schema", "hei_fastapi_ddd.contexts.auth.interfaces.http.auth_schemas"),
        ("app.modules.auth.session_schema", "hei_fastapi_ddd.contexts.auth.interfaces.http.session_schemas"),
        ("app.modules.auth.login_service", "hei_fastapi_ddd.contexts.auth.application.login_service"),
        ("app.modules.auth.register_service", "hei_fastapi_ddd.contexts.auth.application.register_service"),
        ("app.modules.auth.bind_service", "hei_fastapi_ddd.contexts.auth.application.bind_service"),
        ("app.modules.auth.lifecycle_service", "hei_fastapi_ddd.contexts.auth.application.lifecycle_service"),
        ("app.modules.auth.password_change", "hei_fastapi_ddd.contexts.auth.application.password_change"),
        ("app.modules.auth.password_reset_service", "hei_fastapi_ddd.contexts.auth.application.password_reset_service"),
        ("app.modules.auth.protection", "hei_fastapi_ddd.contexts.auth.application.protection"),
        ("app.modules.auth.policy", "hei_fastapi_ddd.contexts.auth.domain.policy"),
        ("app.modules.auth.base", "hei_fastapi_ddd.contexts.auth.application.base"),
        ("app.modules.auth.session_admin_service", "hei_fastapi_ddd.contexts.auth.application.session_admin_service"),
        ("app.modules.auth.oauth.model", "hei_fastapi_ddd.contexts.auth.infrastructure.persistence.oauth_po"),
        ("app.modules.auth.oauth.repository", "hei_fastapi_ddd.contexts.auth.infrastructure.persistence.oauth_repository"),
        ("app.modules.auth.oauth.service", "hei_fastapi_ddd.contexts.auth.application.oauth.oauth_application_service"),
        ("app.modules.auth.oauth.schema", "hei_fastapi_ddd.contexts.auth.interfaces.http.oauth_schemas"),
        ("app.modules.auth.oauth.client", "hei_fastapi_ddd.contexts.auth.infrastructure.oauth.client"),
        ("app.modules.auth.oauth.provider", "hei_fastapi_ddd.contexts.auth.infrastructure.oauth.provider"),
        ("app.modules.auth.oauth.stores", "hei_fastapi_ddd.contexts.auth.infrastructure.oauth.stores"),
        # iam others
        ("app.modules.iam.client.model", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.client_po"),
        ("app.modules.iam.client.repository", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.client_repository"),
        ("app.modules.iam.client.service", "hei_fastapi_ddd.contexts.iam.application.client.client_application_service"),
        ("app.modules.iam.client.schema", "hei_fastapi_ddd.contexts.iam.interfaces.http.client_schemas"),
        ("app.modules.iam.dept.model", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.dept_po"),
        ("app.modules.iam.dept.repository", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.dept_repository"),
        ("app.modules.iam.dept.service", "hei_fastapi_ddd.contexts.iam.application.dept.dept_application_service"),
        ("app.modules.iam.dept.schema", "hei_fastapi_ddd.contexts.iam.interfaces.http.dept_schemas"),
        ("app.modules.iam.dept.resolver", "hei_fastapi_ddd.contexts.iam.infrastructure.dept_resolver"),
        ("app.modules.iam.group.model", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.group_po"),
        ("app.modules.iam.group.repository", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.group_repository"),
        ("app.modules.iam.group.service", "hei_fastapi_ddd.contexts.iam.application.group.group_application_service"),
        ("app.modules.iam.group.schema", "hei_fastapi_ddd.contexts.iam.interfaces.http.group_schemas"),
        ("app.modules.iam.position.model", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.position_po"),
        ("app.modules.iam.position.repository", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.position_repository"),
        ("app.modules.iam.position.service", "hei_fastapi_ddd.contexts.iam.application.position.position_application_service"),
        ("app.modules.iam.position.schema", "hei_fastapi_ddd.contexts.iam.interfaces.http.position_schemas"),
        ("app.modules.iam.resource.model", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po"),
        ("app.modules.iam.resource.repository", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_repository"),
        ("app.modules.iam.resource.service", "hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service"),
        ("app.modules.iam.resource.schema", "hei_fastapi_ddd.contexts.iam.interfaces.http.resource_schemas"),
        ("app.modules.iam.role.model", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po"),
        ("app.modules.iam.role.repository", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_repository"),
        ("app.modules.iam.role.service", "hei_fastapi_ddd.contexts.iam.application.role.role_application_service"),
        ("app.modules.iam.role.schema", "hei_fastapi_ddd.contexts.iam.interfaces.http.role_schemas"),
        ("app.modules.iam.role.constants", "hei_fastapi_ddd.contexts.iam.domain.role.constants"),
        ("app.modules.iam.relation.model", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_po"),
        ("app.modules.iam.relation.repository", "hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository"),
        ("app.modules.iam.enums", "hei_fastapi_ddd.contexts.iam.domain.enums"),
        ("app.modules.iam.schema", "hei_fastapi_ddd.contexts.iam.interfaces.http.iam_schemas"),
        ("app.modules.iam.reference_guard", "hei_fastapi_ddd.contexts.iam.application.reference_guard"),
        ("app.modules.iam.support.audit", "hei_fastapi_ddd.contexts.iam.application.support.audit"),
        ("app.modules.iam.support", "hei_fastapi_ddd.contexts.iam.application.support"),
        # profile
        ("app.modules.profile.admin.model", "hei_fastapi_ddd.contexts.profile.infrastructure.persistence.admin_po"),
        ("app.modules.profile.admin.repository", "hei_fastapi_ddd.contexts.profile.infrastructure.persistence.admin_repository"),
        ("app.modules.profile.admin.service", "hei_fastapi_ddd.contexts.profile.application.admin.admin_application_service"),
        ("app.modules.profile.admin.schema", "hei_fastapi_ddd.contexts.profile.interfaces.http.admin_schemas"),
        ("app.modules.profile.portal.model", "hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_po"),
        ("app.modules.profile.portal.repository", "hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_repository"),
        ("app.modules.profile.portal.service", "hei_fastapi_ddd.contexts.profile.application.portal.portal_application_service"),
        ("app.modules.profile.portal.schema", "hei_fastapi_ddd.contexts.profile.interfaces.http.portal_schemas"),
        ("app.modules.profile.identity.model", "hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_po"),
        ("app.modules.profile.identity.repository", "hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_repository"),
        ("app.modules.profile.identity.service", "hei_fastapi_ddd.contexts.profile.application.identity.identity_application_service"),
        ("app.modules.profile.identity.schema", "hei_fastapi_ddd.contexts.profile.interfaces.http.identity_schemas"),
        ("app.modules.profile.identity.crypto", "hei_fastapi_ddd.contexts.profile.application.identity.crypto"),
        ("app.modules.profile.identity.enums", "hei_fastapi_ddd.contexts.profile.domain.identity.enums"),
        ("app.modules.profile.identity.handlers", "hei_fastapi_ddd.contexts.profile.application.identity.handlers"),
        ("app.modules.profile.identity.support", "hei_fastapi_ddd.contexts.profile.application.identity.support"),
        ("app.modules.profile.identity.providers", "hei_fastapi_ddd.contexts.profile.infrastructure.identity_providers"),
        ("app.modules.profile.schema", "hei_fastapi_ddd.contexts.profile.interfaces.http.profile_schemas"),
        ("app.modules.profile.utils.profile", "hei_fastapi_ddd.contexts.profile.application.utils.profile"),
        ("app.modules.profile.utils", "hei_fastapi_ddd.contexts.profile.application.utils"),
        # sys others
        ("app.modules.sys.audit.outbox", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_outbox"),
        ("app.modules.sys.audit.event_handler", "hei_fastapi_ddd.contexts.sys.infrastructure.audit_event_handler"),
        ("app.modules.sys.audit.labels", "hei_fastapi_ddd.contexts.sys.infrastructure.audit_labels"),
        ("app.modules.sys.audit.model", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_po"),
        ("app.modules.sys.audit.alert_model", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_alert_po"),
        ("app.modules.sys.audit.repository", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_repository"),
        ("app.modules.sys.audit.service", "hei_fastapi_ddd.contexts.sys.application.audit.audit_application_service"),
        ("app.modules.sys.audit.schema", "hei_fastapi_ddd.contexts.sys.interfaces.http.audit_schemas"),
        ("app.modules.sys.audit.alert", "hei_fastapi_ddd.contexts.sys.application.audit.alert"),
        ("app.modules.sys.audit.analyzer", "hei_fastapi_ddd.contexts.sys.application.audit.analyzer"),
        ("app.modules.sys.audit.support", "hei_fastapi_ddd.contexts.sys.application.audit.support"),
        ("app.modules.sys.audit.tasks", "hei_fastapi_ddd.contexts.sys.application.audit.tasks"),
        ("app.modules.sys.job.scheduler", "hei_fastapi_ddd.contexts.sys.infrastructure.job_scheduler"),
        ("app.modules.sys.job.model", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.job_po"),
        ("app.modules.sys.job.repository", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.job_repository"),
        ("app.modules.sys.job.service", "hei_fastapi_ddd.contexts.sys.application.job.job_application_service"),
        ("app.modules.sys.job.schema", "hei_fastapi_ddd.contexts.sys.interfaces.http.job_schemas"),
        ("app.modules.sys.job.cron", "hei_fastapi_ddd.contexts.sys.application.job.cron"),
        ("app.modules.sys.job.execution", "hei_fastapi_ddd.contexts.sys.application.job.execution"),
        ("app.modules.sys.job.registry", "hei_fastapi_ddd.contexts.sys.application.job.registry"),
        ("app.modules.sys.job.sample", "hei_fastapi_ddd.contexts.sys.application.job.sample"),
        ("app.modules.sys.job.tasks", "hei_fastapi_ddd.contexts.sys.application.job.tasks"),
        ("app.modules.sys.banner.model", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.banner_po"),
        ("app.modules.sys.banner.repository", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.banner_repository"),
        ("app.modules.sys.banner.service", "hei_fastapi_ddd.contexts.sys.application.banner.banner_application_service"),
        ("app.modules.sys.banner.schema", "hei_fastapi_ddd.contexts.sys.interfaces.http.banner_schemas"),
        ("app.modules.sys.banner.enums", "hei_fastapi_ddd.contexts.sys.domain.banner.enums"),
        ("app.modules.sys.banner.tasks", "hei_fastapi_ddd.contexts.sys.application.banner.tasks"),
        ("app.modules.sys.codegen.model", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.codegen_po"),
        ("app.modules.sys.codegen.repository", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.codegen_repository"),
        ("app.modules.sys.codegen.service", "hei_fastapi_ddd.contexts.sys.application.codegen.codegen_application_service"),
        ("app.modules.sys.codegen.schema", "hei_fastapi_ddd.contexts.sys.interfaces.http.codegen_schemas"),
        ("app.modules.sys.codegen.apply", "hei_fastapi_ddd.contexts.sys.application.codegen.apply"),
        ("app.modules.sys.codegen.paths", "hei_fastapi_ddd.contexts.sys.application.codegen.paths"),
        ("app.modules.sys.codegen.templates", "hei_fastapi_ddd.contexts.sys.application.codegen.templates"),
        ("app.modules.sys.config.repository", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.config_repository"),
        ("app.modules.sys.config.service", "hei_fastapi_ddd.contexts.sys.application.config.config_application_service"),
        ("app.modules.sys.config.schema", "hei_fastapi_ddd.contexts.sys.interfaces.http.config_schemas"),
        ("app.modules.sys.feedback.model", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.feedback_po"),
        ("app.modules.sys.feedback.repository", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.feedback_repository"),
        ("app.modules.sys.feedback.service", "hei_fastapi_ddd.contexts.sys.application.feedback.feedback_application_service"),
        ("app.modules.sys.feedback.schema", "hei_fastapi_ddd.contexts.sys.interfaces.http.feedback_schemas"),
        ("app.modules.sys.feedback.enums", "hei_fastapi_ddd.contexts.sys.domain.feedback.enums"),
        ("app.modules.sys.file.model", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.file_po"),
        ("app.modules.sys.file.repository", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.file_repository"),
        ("app.modules.sys.file.service", "hei_fastapi_ddd.contexts.sys.application.file.file_application_service"),
        ("app.modules.sys.file.schema", "hei_fastapi_ddd.contexts.sys.interfaces.http.file_schemas"),
        ("app.modules.sys.file.content_disposition", "hei_fastapi_ddd.contexts.sys.application.file.content_disposition"),
        ("app.modules.sys.notice.model", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.notice_po"),
        ("app.modules.sys.notice.repository", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.notice_repository"),
        ("app.modules.sys.notice.service", "hei_fastapi_ddd.contexts.sys.application.notice.notice_application_service"),
        ("app.modules.sys.notice.schema", "hei_fastapi_ddd.contexts.sys.interfaces.http.notice_schemas"),
        ("app.modules.sys.notice.enums", "hei_fastapi_ddd.contexts.sys.domain.notice.enums"),
        ("app.modules.sys.notice.target_scope", "hei_fastapi_ddd.contexts.sys.application.notice.target_scope"),
        ("app.modules.sys.public.site_footer", "hei_fastapi_ddd.contexts.sys.application.public.site_footer"),
        ("app.modules.sys.weak_password.repository", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.weak_password_repository"),
        ("app.modules.sys.weak_password.service", "hei_fastapi_ddd.contexts.sys.application.weak_password.weak_password_application_service"),
        ("app.modules.sys.weak_password.schema", "hei_fastapi_ddd.contexts.sys.interfaces.http.weak_password_schemas"),
        ("app.modules.sys.workspace.model", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.workspace_po"),
        ("app.modules.sys.workspace.repository", "hei_fastapi_ddd.contexts.sys.infrastructure.persistence.workspace_repository"),
        ("app.modules.sys.workspace.service", "hei_fastapi_ddd.contexts.sys.application.workspace.workspace_application_service"),
        ("app.modules.sys.workspace.schema", "hei_fastapi_ddd.contexts.sys.interfaces.http.workspace_schemas"),
        # biz
        ("app.modules.biz.cg_test_activity.model", "hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_activity_po"),
        ("app.modules.biz.cg_test_activity.repository", "hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_activity_repository"),
        ("app.modules.biz.cg_test_activity.service", "hei_fastapi_ddd.contexts.biz.application.cg_test_activity.cg_test_activity_application_service"),
        ("app.modules.biz.cg_test_activity.schema", "hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_activity_schemas"),
        ("app.modules.biz.cg_test_catalog.model", "hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_catalog_po"),
        ("app.modules.biz.cg_test_catalog.repository", "hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_catalog_repository"),
        ("app.modules.biz.cg_test_catalog.service", "hei_fastapi_ddd.contexts.biz.application.cg_test_catalog.cg_test_catalog_application_service"),
        ("app.modules.biz.cg_test_catalog.schema", "hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_catalog_schemas"),
        ("app.modules.biz.cg_test_knowledge_category.model", "hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_knowledge_category_po"),
        ("app.modules.biz.cg_test_knowledge_category.repository", "hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_knowledge_category_repository"),
        ("app.modules.biz.cg_test_knowledge_category.service", "hei_fastapi_ddd.contexts.biz.application.cg_test_knowledge_category.cg_test_knowledge_category_application_service"),
        ("app.modules.biz.cg_test_knowledge_category.schema", "hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_knowledge_category_schemas"),
        ("app.modules.biz.cg_test_order.model", "hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_order_po"),
        ("app.modules.biz.cg_test_order.repository", "hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_order_repository"),
        ("app.modules.biz.cg_test_order.service", "hei_fastapi_ddd.contexts.biz.application.cg_test_order.cg_test_order_application_service"),
        ("app.modules.biz.cg_test_order.schema", "hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_order_schemas"),
    ]
    pairs.extend(aliases)
    pairs.extend(fallbacks)
    # 去重，最长优先
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for old, new in sorted(pairs, key=lambda x: len(x[0]), reverse=True):
        if old in seen:
            continue
        seen.add(old)
        unique.append((old, new))
    return unique


CORE_REWRITES = [
    ("app.core.response", "hei_fastapi_ddd.shared.web"),
    ("app.core.db", "hei_fastapi_ddd.shared.persistence"),
    ("app.core.cache", "hei_fastapi_ddd.shared.redis"),
    ("app.core.events", "hei_fastapi_ddd.shared.messaging"),
    ("app.middleware", "hei_fastapi_ddd.shared.middleware"),
    ("app.deps", "hei_fastapi_ddd.shared.deps"),
    ("app.core", "hei_fastapi_ddd.shared"),
]


def rewrite_imports(text: str, module_rewrites: list[tuple[str, str]]) -> str:
    """按最长匹配重写 import 路径。"""

    def replace_mod(mod: str) -> str:
        for old, new in module_rewrites:
            if mod == old or mod.startswith(old + "."):
                return new + mod[len(old) :]
        for old, new in CORE_REWRITES:
            if mod == old or mod.startswith(old + "."):
                return new + mod[len(old) :]
        return mod

    def from_repl(m: re.Match[str]) -> str:
        mod = replace_mod(m.group(1))
        return f"from {mod} import {m.group(2)}"

    def import_repl(m: re.Match[str]) -> str:
        mods = m.group(1)
        parts = []
        for part in mods.split(","):
            part = part.strip()
            if not part:
                continue
            # handle "x as y"
            name, *rest = part.split(" as ")
            name = replace_mod(name.strip())
            if rest:
                parts.append(f"{name} as {rest[0].strip()}")
            else:
                parts.append(name)
        return "import " + ", ".join(parts)

    text = re.sub(r"^from\s+([\w.]+)\s+import\s+(.+)$", from_repl, text, flags=re.M)
    text = re.sub(r"^import\s+([\w.,\s]+)$", import_repl, text, flags=re.M)
    return text


DOMAIN_FEATURES = [
    # (context, feature, entity_class, po_module_leaf, po_class)
    ("sys", "dict", "DictAggregate", "dict_po", "SysDict"),
    ("sys", "banner", "Banner", "banner_po", "SysBanner"),
    ("sys", "feedback", "Feedback", "feedback_po", "SysFeedback"),
    ("sys", "file", "FileObject", "file_po", "SysFile"),
    ("sys", "notice", "Notice", "notice_po", "SysNotice"),
    ("sys", "job", "Job", "job_po", "SysJob"),
    ("sys", "workspace", "WorkspaceShortcut", "workspace_po", "SysWorkspaceShortcut"),
    ("sys", "codegen", "CodegenTable", "codegen_po", "SysCodegenTable"),
    ("sys", "audit", "AuditLog", "audit_po", "SysAuditLog"),
    ("iam", "account", "Account", "account_po", "SysAccount"),
    ("iam", "client", "Client", "client_po", "SysClient"),
    ("iam", "dept", "Dept", "dept_po", "SysDept"),
    ("iam", "group", "Group", "group_po", "SysGroup"),
    ("iam", "position", "Position", "position_po", "SysPosition"),
    ("iam", "resource", "Resource", "resource_po", "SysResource"),
    ("iam", "role", "Role", "role_po", "SysRole"),
    ("profile", "admin", "AdminProfile", "admin_po", "ProfileUserAdmin"),
    ("profile", "portal", "PortalProfile", "portal_po", "ProfileUserPortal"),
    ("profile", "identity", "IdentityCase", "identity_po", "ProfileIdentityCase"),
    ("biz", "cg_test_activity", "CgTestActivity", "cg_test_activity_po", "CgTestActivity"),
    ("biz", "cg_test_catalog", "CgTestCatalog", "cg_test_catalog_po", "CgTestCatalog"),
    ("biz", "cg_test_knowledge_category", "CgTestKnowledgeCategory", "cg_test_knowledge_category_po", "CgTestKnowledgeCategory"),
    ("biz", "cg_test_order", "CgTestOrder", "cg_test_order_po", "CgTestOrder"),
    ("auth", "oauth", "OAuthBinding", "oauth_po", "OAuthBinding"),
]


def write_domain_stubs() -> None:
    """为各 feature 生成最小领域实体与仓储协议（dict/account 稍后深度覆盖）。"""
    for ctx, feature, entity, _po, _po_cls in DOMAIN_FEATURES:
        if feature in ("dict", "account"):
            continue
        domain_dir = DEST / ctx / "domain" / feature
        domain_dir.mkdir(parents=True, exist_ok=True)
        (domain_dir / "__init__.py").write_text("", encoding="utf-8")
        agg = domain_dir / "aggregate.py"
        if not agg.exists():
            agg.write_text(
                f'''""" Author: Charlie

{feature} 领域实体。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hei_fastapi_ddd.ddd_kernel.entity import AggregateRoot
from hei_fastapi_ddd.ddd_kernel.domain_exception import DomainException


@dataclass
class {entity}(AggregateRoot[str]):
    """{feature} 聚合根，承载基础状态校验。"""

    id: str
    status: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self, self.id)

    def ensure_required(self, *fields: str) -> None:
        """校验必填字段非空。"""
        # 1. 逐字段检查
        for name in fields:
            value = getattr(self, name, None) if hasattr(self, name) else self.extra.get(name)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise DomainException(f"{{name}} is required")

    def change_status(self, new_status: str, *, allowed: set[str] | None = None) -> None:
        """变更状态；可选限制合法目标集合。"""
        # 1. 校验目标状态
        if allowed is not None and new_status not in allowed:
            raise DomainException(f"Invalid status transition to {{new_status}}")
        # 2. 写入新状态
        self.status = new_status
''',
                encoding="utf-8",
            )
        repo = domain_dir / "repository.py"
        if not repo.exists():
            repo.write_text(
                f'''""" Author: Charlie

{feature} 仓储端口。
"""

from __future__ import annotations

from typing import Protocol

from hei_fastapi_ddd.contexts.{ctx}.domain.{feature}.aggregate import {entity}


class {entity}Repository(Protocol):
    """{feature} 仓储协议。"""

    async def find_by_id(self, id: str) -> {entity} | None:
        """按主键查找。"""
        ...

    async def save(self, entity: {entity}) -> {entity}:
        """持久化聚合。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...
''',
                encoding="utf-8",
            )


def ensure_init_files(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_dir() and not path.name.startswith("__"):
            init = path / "__init__.py"
            if not init.exists():
                init.write_text("", encoding="utf-8")


def main() -> None:
    module_rewrites = build_module_rewrites()
    copied = 0
    skipped = 0
    for old_rel, new_rel in EXPLICIT.items():
        src = SRC / old_rel
        if not src.exists():
            # weak_password may lack service.py
            print(f"SKIP missing: {old_rel}")
            skipped += 1
            continue
        dest = DEST / new_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        text = rewrite_imports(text, module_rewrites)
        dest.write_text(text, encoding="utf-8")
        copied += 1

    write_domain_stubs()
    ensure_init_files(DEST)
    print(f"Copied {copied}, skipped {skipped}")


if __name__ == "__main__":
    main()
