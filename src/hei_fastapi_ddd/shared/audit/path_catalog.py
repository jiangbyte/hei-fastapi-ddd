""" Author: Charlie

由 API 路径推导审计 resource_type / action（对齐 hei-boot @OperationAudit 声明）。
"""

from __future__ import annotations

from hei_fastapi_ddd.contexts.sys.infrastructure.audit_labels import normalize_action

_MODULE_RESOURCE: dict[str, str] = {
    "sys/accounts": "iam_account",
    "sys/roles": "iam_role",
    "sys/depts": "iam_dept",
    "sys/groups": "iam_group",
    "sys/positions": "iam_position",
    "sys/resources": "iam_resource",
    "sys/resource-modules": "iam_resourcemodule",
    "sys/resource-buttons": "iam_resource",
    "sys/client-modules": "iam_clientmodule",
    "sys/client-resources": "iam_clientresource",
    "sys/config": "sys_config",
    "sys/dicts": "sys_dict",
    "sys/jobs": "sys_job",
    "sys/banners": "sys_banner",
    "sys/notices": "sys_notice",
    "sys/feedback": "sys_feedback",
    "sys/files": "sys_file",
    "sys/codegen": "sys_codegen",
    "sys/weak-passwords": "sys_weakpassword",
    "sys/real-name-case": "real_name_case",
    "sys/identity": "profile_identity",
    "real-name/case": "real_name_case",
    "profile": "profile_center",
    "auth/sessions": "auth_session",
    "logout": "auth",
    "sys/workspace/shortcuts": "workspace_shortcut",
}

_ACTION_OVERRIDES: dict[tuple[str, str], str] = {
    ("profile", "update"): "update_profile",
    ("profile/password", "update"): "update_password",
    ("profile/phone", "update"): "update_phone",
    ("profile/email", "update"): "update_email",
    ("profile/avatar", "upload"): "upload_avatar",
    ("sys/workspace/shortcuts", "post"): "update",
    ("logout", "post"): "logout",
    ("forgot-password/phone", "post"): "forgot_password_phone",
    ("reset-password/phone", "post"): "reset_password_phone",
    ("sys/config", "batch_save"): "batch_save",
}


def resolve_audit_target(module_path: str, action: str) -> tuple[str, str]:
    """将 URL 模块路径与动作规范为 hei-boot 风格的 resource_type、action。"""
    path_key = module_path.strip("/").lower()
    act = normalize_action(action)
    resource_type = _resolve_resource_type(path_key)
    resolved_action = _ACTION_OVERRIDES.get((path_key, act), act)
    return resource_type, resolved_action


def _resolve_resource_type(path_key: str) -> str:
    if path_key in _MODULE_RESOURCE:
        return _MODULE_RESOURCE[path_key]

    best_match: str | None = None
    best_len = -1
    for prefix, resource_type in _MODULE_RESOURCE.items():
        if path_key == prefix or path_key.startswith(f"{prefix}/"):
            if len(prefix) > best_len:
                best_match = resource_type
                best_len = len(prefix)
    if best_match is not None:
        return best_match

    if path_key.startswith("biz/"):
        slug = path_key.split("/", 2)[1]
        return f"biz_{slug.replace('-', '')}"

    return path_key.replace("/", "_").replace("-", "_")
