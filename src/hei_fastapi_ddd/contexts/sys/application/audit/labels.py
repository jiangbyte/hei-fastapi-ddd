""" Author: Charlie

审计展示文案（对齐 hei-boot AuditLabelCatalog）。
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwordhash",
        "password_hash",
        "oldpassword",
        "old_password",
        "newpassword",
        "new_password",
        "token",
        "secret",
        "accesskey",
        "access_key",
        "privatekey",
        "private_key",
        "cryptokey",
        "crypto_key",
        "realname",
        "real_name",
        "realnamecipher",
        "real_name_cipher",
        "documentno",
        "document_no",
        "documentnocipher",
        "document_no_cipher",
        "documentnohash",
        "document_no_hash",
        "applicantcontact",
        "applicant_contact",
        "attachmentids",
        "attachment_ids",
        "providerorderno",
        "provider_order_no",
        "providerpayload",
        "provider_payload",
        "reviewremark",
        "review_remark",
    }
)

FIELD_LABELS: dict[str, str] = {
    "id": "编号",
    "name": "名称",
    "code": "编码",
    "title": "标题",
    "label": "标签",
    "value": "值",
    "account": "账号",
    "nickname": "昵称",
    "username": "用户名",
    "email": "邮箱",
    "phone": "手机号",
    "status": "状态",
    "sort": "排序",
    "remark": "备注",
    "description": "描述",
    "category": "分类",
    "type": "类型",
    "scopeType": "范围类型",
    "scope_type": "范围类型",
    "dataScope": "数据范围",
    "data_scope": "数据范围",
    "ownerDeptId": "所属部门",
    "owner_dept_id": "所属部门",
    "parentId": "上级",
    "parent_id": "上级",
    "content": "内容",
    "summary": "摘要",
    "enabled": "启用",
    "pinned": "置顶",
    "publishStatus": "发布状态",
    "publish_status": "发布状态",
    "avatar": "头像",
    "avatarUrl": "头像",
    "avatar_url": "头像",
    "originalName": "文件名",
    "original_name": "文件名",
    "fileName": "文件名",
    "cron": "Cron",
    "cronExpression": "Cron",
    "handlerName": "处理器",
    "handler_name": "处理器",
    "roleIds": "角色",
    "role_ids": "角色",
    "deptIds": "部门",
    "dept_ids": "部门",
    "groupIds": "用户组",
    "group_ids": "用户组",
    "positionIds": "岗位",
    "position_ids": "岗位",
    "accountIds": "账号",
    "account_ids": "账号",
    "grantInfoList": "授权资源",
    "grant_info_list": "授权资源",
    "passwordHash": "密码",
    "password_hash": "密码",
    "businessType": "认证方式",
    "business_type": "认证方式",
    "documentType": "证件类型",
    "document_type": "证件类型",
    "caseId": "工单编号",
    "case_id": "工单编号",
    "reviewRemark": "审核意见",
    "review_remark": "审核意见",
    "providerCode": "认证渠道",
    "provider_code": "认证渠道",
}

_PATH_SUMMARY_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+/", re.IGNORECASE)


def is_path_summary(summary: str | None) -> bool:
    """是否为中间件自动填充的 METHOD path 摘要。"""
    return bool(summary and _PATH_SUMMARY_RE.match(str(summary).strip()))


IDENTITY_ENUM_LABELS: dict[str, str] = {
    "ID_CARD": "身份证",
    "PASSPORT": "护照",
    "ACCOUNT_VERIFY": "人工审核",
    "THIRD_PARTY": "第三方认证",
    "EID": "电子身份证",
}


def normalize_action(action: str | None) -> str:
    return (action or "").strip().lower().replace("-", "_")


def normalize_account_type(value: str | None) -> str | None:
    if not value or not str(value).strip():
        return None
    return str(value).strip().lower()


def module_label(resource_type: str | None) -> str:
    if not resource_type or not str(resource_type).strip():
        return "系统"
    key = str(resource_type).strip().lower()
    mapping = {
        "auth": "认证 - 账号",
        "account": "认证 - 账号",
        "auth_session": "认证 - 会话",
        "iam_account": "权限 - 账号",
        "iam_role": "权限 - 角色",
        "iam_dept": "权限 - 部门",
        "iam_group": "权限 - 用户组",
        "iam_position": "权限 - 岗位",
        "iam_resource": "权限 - 资源",
        "resources": "权限 - 资源",
        "iam_client_module": "权限 - 客户端模块",
        "iam_client_resource": "权限 - 客户端资源",
        "sys_notice": "系统 - 消息",
        "sys_banner": "系统 - 展示图",
        "sys_file": "系统 - 文件",
        "sys_config": "系统 - 配置",
        "sys_dict": "系统 - 字典",
        "sys_job": "系统 - 任务",
        "sys_feedback": "系统 - 反馈",
        "sys_codegen": "系统 - 代码生成",
        "sys_weakpassword": "系统 - 弱密码",
        "profile_center": "个人中心",
        "real_name_case": "实名认证 - 工单",
        "profile_identity": "实名认证 - 身份",
        "workspace_shortcut": "工作台 - 快捷应用",
    }
    if key in mapping:
        return mapping[key]
    if key.startswith("biz_"):
        return f"业务 - {key[4:]}"
    if key.startswith("sys_"):
        return f"系统 - {key[4:]}"
    if key.startswith("iam_"):
        return f"权限 - {key[4:]}"
    return resource_type


def entity_short_name(resource_type: str | None) -> str:
    label = module_label(resource_type)
    if " - " in label:
        return label.split(" - ", 1)[1]
    return label


def action_name(
    resource_type: str | None,
    action: str | None,
    explicit: str | None = None,
) -> str:
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    act = normalize_action(action)
    short = entity_short_name(resource_type)
    names = {
        "create": f"创建{short}",
        "update": f"更新{short}",
        "delete": f"删除{short}",
        "login": "登录",
        "logout": "退出登录",
        "register": "注册",
        "refresh": "刷新令牌",
        "upload": "上传文件",
        "publish": f"发布{short}",
        "revoke": f"撤回{short}",
        "pin": f"置顶{short}",
        "read": f"阅读{short}",
        "read_all": f"阅读{short}",
        "export": f"导出{short}",
        "import": f"导入{short}",
        "enabled": f"启用{short}",
        "enable": f"启用{short}",
        "run": f"执行{short}",
        "submit": f"提交{short}",
        "approve": f"审核通过{short}",
        "reject": f"审核驳回{short}",
        "init_third_party": "发起第三方实名",
        "callback": "第三方实名回调",
        "batch_save": f"批量保存{short}",
        "forgot_password": "忘记密码",
        "forgot_password_phone": "手机找回密码",
        "reset_password": "重置密码",
        "reset_password_phone": "手机重置密码",
        "update_password": "修改密码",
        "update_login_identity": "更新登录标识",
        "update_profile": "更新资料",
        "upload_avatar": "上传头像",
        "update_phone": "绑定手机号",
        "update_email": "绑定邮箱",
        "cancel": "注销账号",
        "interaction": "互动",
        "oauth_wechat_mp_login": "微信小程序登录",
        "oauth_bind_authorize": "三方账号绑定",
        "oauth_unbind": "解绑三方账号",
        "test_webhook": "测试审计 Webhook",
        "test_push": "测试审计推送",
        "grant": f"授权{short}",
        "grant_resources": f"授权{short}",
        "grant_users": f"授权{short}",
        "grant_roles": f"授权{short}",
        "grant_groups": f"授权{short}",
        "grant_depts": f"授权{short}",
        "grant_client_resources": f"授权{short}",
        "grant_resource": f"授权{short}",
        "grant_user": f"授权{short}",
        "grant_client_resource": f"授权{short}",
        "exit": "强制下线",
        "token_exit": "强制下线",
    }
    if act in names:
        return names[act]
    return action or "操作"


def action_type(action: str | None, explicit: str | None = None) -> str:
    if explicit and str(explicit).strip():
        return str(explicit).strip().upper()
    act = normalize_action(action)
    if act in {"create", "register", "submit"}:
        return "CREATE"
    if act in {
        "update",
        "update_password",
        "update_profile",
        "update_phone",
        "update_email",
        "batch_save",
        "pin",
        "publish",
        "revoke",
        "enabled",
        "enable",
        "approve",
        "reject",
        "grant",
        "grant_resources",
        "grant_users",
        "grant_roles",
        "grant_groups",
        "grant_depts",
        "grant_client_resources",
        "grant_resource",
        "grant_user",
        "grant_client_resource",
        "update_login_identity",
    }:
        return "UPDATE"
    if act in {"delete", "cancel"}:
        return "DELETE"
    if act in {"login", "oauth_wechat_mp_login"}:
        return "LOGIN"
    if act == "logout":
        return "LOGOUT"
    if act == "export":
        return "EXPORT"
    if act in {"read", "read_all", "refresh", "page", "detail", "list"}:
        return "QUERY"
    return "OTHER"


def field_label(key: str | None) -> str:
    if not key or not str(key).strip():
        return "字段"
    direct = FIELD_LABELS.get(key)
    if direct:
        return direct
    snake = re.sub(r"([a-z])([A-Z])", r"\1_\2", key).lower()
    from_snake = FIELD_LABELS.get(snake)
    if from_snake:
        return from_snake
    return key


def build_content(
    action: str | None,
    resource_type: str | None,
    action_name_text: str | None,
    subject: str | None,
    success: bool,
    before_data: Mapping[str, Any] | None = None,
    after_data: Mapping[str, Any] | None = None,
) -> str:
    """生成可读审计摘要（对齐 hei-boot buildContent）。"""
    act = normalize_action(action)
    entity = entity_short_name(resource_type)
    subject_part = f" 【{str(subject).strip()}】" if subject and str(subject).strip() else ""
    result = "成功" if success else "失败"
    resource_key = (resource_type or "").strip().lower()

    identity_content = _build_identity_content(act, resource_key, subject_part, success, after_data, before_data)
    if identity_content:
        return identity_content

    if act == "login":
        return f"账号{subject_part}登录{result}"
    if act == "logout":
        return f"账号{subject_part}退出{result}"
    if act == "register":
        return f"账号{subject_part}注册{result}"
    if act == "oauth_wechat_mp_login":
        return f"账号{subject_part}通过微信小程序登录{result}"
    if act == "oauth_bind_authorize":
        diff = format_diff(before_data, after_data)
        if diff:
            return f"发起三方账号绑定{subject_part}：{diff}"
        return f"发起三方账号绑定{subject_part}{result}"
    if act in {"reset_password", "reset-password"}:
        pwd_diff = _password_reset_diff(before_data, after_data)
        if pwd_diff:
            return f"将{entity}{subject_part}的{pwd_diff}"
        return f"重置了{entity}{subject_part}的密码"
    if act in {"update_password", "update-password"}:
        return f"修改了{entity}{subject_part}的密码"
    if act in {"delete", "cancel"}:
        return f"删除了{entity}{subject_part}"

    verb = _action_verb(act)
    diff = format_diff(before_data, after_data)
    if verb:
        if diff:
            return f"{verb}{entity}{subject_part}：{diff}"
        name = action_name_text if action_name_text else f"{verb}{entity}"
        return f"{name}{subject_part}" + ("" if success else "失败")

    name = action_name_text if action_name_text else "操作"
    if diff:
        return f"【{name}】{result}：{diff}"
    return f"【{name}】{subject_part}{result}"


def format_diff(
    before_data: Mapping[str, Any] | None,
    after_data: Mapping[str, Any] | None,
) -> str | None:
    if not before_data and not after_data:
        return None
    before = dict(before_data or {})
    after = dict(after_data or {})
    keys: dict[str, None] = {}
    for key in before:
        keys[key] = None
    for key in after:
        keys[key] = None
    parts: list[str] = []
    for key in keys:
        if _should_skip_field(key):
            continue
        old_val = before.get(key)
        new_val = after.get(key)
        if _equals_loose(old_val, new_val):
            continue
        label = field_label(key)
        if isinstance(old_val, Iterable) and not isinstance(old_val, (str, bytes, dict)) or (
            isinstance(new_val, Iterable) and not isinstance(new_val, (str, bytes, dict))
        ):
            parts.append(f"【{label}】{_collection_change_text(old_val, new_val)}")
        else:
            parts.append(
                f"【{label}】从【{_display_value(old_val)}】修改为【{_display_value(new_val)}】"
            )
    return "；".join(parts) if parts else None


def _action_verb(act: str) -> str | None:
    verbs = {
        "create": "创建了",
        "submit": "创建了",
        "update": "更新了",
        "update_profile": "更新了",
        "update_phone": "更新了",
        "update_email": "更新了",
        "batch_save": "更新了",
        "enabled": "更新了",
        "enable": "更新了",
        "pin": "更新了",
        "publish": "更新了",
        "revoke": "更新了",
        "approve": "更新了",
        "reject": "更新了",
        "upload": "上传了",
        "upload_avatar": "上传了",
        "run": "执行了",
        "read": "阅读了",
        "read_all": "阅读了",
        "interaction": "互动了",
        "test_webhook": "测试了",
        "test_push": "测试了",
        "grant": "授权了",
        "grant_resources": "授权了",
        "grant_users": "授权了",
        "grant_roles": "授权了",
        "grant_groups": "授权了",
        "grant_depts": "授权了",
        "grant_client_resources": "授权了",
        "grant_resource": "授权了",
        "grant_user": "授权了",
        "grant_client_resource": "授权了",
        "exit": "强制下线了",
        "token_exit": "强制下线了",
    }
    return verbs.get(act)


def _build_identity_content(
    act: str,
    resource_key: str,
    subject_part: str,
    success: bool,
    after_data: Mapping[str, Any] | None,
    before_data: Mapping[str, Any] | None,
) -> str | None:
    result = "成功" if success else "失败"
    if resource_key == "real_name_case":
        if act == "submit":
            return f"提交实名认证{subject_part}{_identity_hint(after_data)}{result}"
        if act == "approve":
            return f"通过实名认证审核{subject_part}{result}"
        if act == "reject":
            remark = _identity_review_remark(after_data, before_data)
            if remark:
                return f"驳回实名认证{subject_part}：{remark}{result}"
            return f"驳回实名认证{subject_part}{result}"
        if act == "init_third_party":
            return f"发起第三方实名认证{subject_part}{_identity_hint(after_data)}{result}"
        if act == "callback":
            return f"第三方实名认证回调{subject_part}{result}"
    if resource_key == "profile_identity" and act == "revoke":
        return f"撤销实名认证{subject_part}{result}"
    return None


def _identity_hint(data: Mapping[str, Any] | None) -> str:
    if not data:
        return ""
    hints: list[str] = []
    for keys in (("businessType", "business_type"), ("documentType", "document_type"), ("providerCode", "provider_code")):
        for key in keys:
            value = data.get(key)
            if value is not None and str(value).strip():
                hints.append(f"{field_label(key)}：{_identity_enum_label(str(value))}")
                break
    return f"（{'，'.join(hints)}）" if hints else ""


def _identity_review_remark(
    after_data: Mapping[str, Any] | None,
    before_data: Mapping[str, Any] | None,
) -> str | None:
    value = _first_present(after_data, "reviewRemark", "review_remark")
    if value is None:
        value = _first_present(before_data, "reviewRemark", "review_remark")
    if value is None or not str(value).strip():
        return None
    return f"【审核意见】{str(value).strip()}"


def _identity_enum_label(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return "空"
    return IDENTITY_ENUM_LABELS.get(value.upper(), value)


def _first_present(data: Mapping[str, Any] | None, *keys: str) -> Any:
    if not data:
        return None
    for key in keys:
        if key in data:
            return data[key]
    return None


def _password_reset_diff(
    before_data: Mapping[str, Any] | None,
    after_data: Mapping[str, Any] | None,
) -> str | None:
    before = dict(before_data or {})
    after = dict(after_data or {})
    old_pwd = _first_present(before, "passwordHash", "password_hash", "password")
    new_pwd = _first_present(after, "passwordHash", "password_hash", "password")
    if old_pwd is None and new_pwd is None:
        return None
    return f"密码从【{_display_value(old_pwd)}】重置为【{_display_value(new_pwd)}】"


def _collection_change_text(old_val: Any, new_val: Any) -> str:
    old_text = _display_value(old_val)
    new_text = _display_value(new_val)
    if old_text == "空" and new_text != "空":
        return f"添加了【{new_text}】"
    if old_text != "空" and new_text == "空":
        return f"删除了【{old_text}】"
    return f"从【{old_text}】修改为【{new_text}】"


def _should_skip_field(key: str) -> bool:
    if not key or not str(key).strip():
        return True
    normalized = re.sub(r"[-_]", "", key).lower()
    if normalized in {"id", "createdat", "updatedat", "createdby", "updatedby"}:
        return True
    return _is_sensitive(key)


def _is_sensitive(key: str) -> bool:
    normalized = re.sub(r"[-_]", "", key).lower()
    for sensitive in SENSITIVE_KEYS:
        if sensitive.replace("_", "") in normalized:
            return True
    return False


def _equals_loose(a: Any, b: Any) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, Iterable) and not isinstance(a, (str, bytes, dict)) or (
        isinstance(b, Iterable) and not isinstance(b, (str, bytes, dict))
    ):
        return _display_value(a) == _display_value(b)
    return str(a) == str(b)


def _display_value(value: Any) -> str:
    if value is None:
        return "空"
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
        items = [str(item) for item in value if item is not None]
        return "，".join(items) if items else "空"
    text = str(value).strip()
    return text if text else "空"
