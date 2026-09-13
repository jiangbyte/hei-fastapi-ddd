""" Author: Charlie

审计叙事文案与路径映射单元测试。
"""

from hei_fastapi_ddd.contexts.sys.infrastructure.audit_labels import build_content, is_path_summary
from hei_fastapi_ddd.shared.audit.path_catalog import resolve_audit_target


def test_build_identity_init_third_party_failure():
  summary = build_content(
      action="init_third_party",
      resource_type="real_name_case",
      action_name_text="发起第三方实名",
      subject="user",
      success=False,
      after_data={
          "business_type": "ACCOUNT_VERIFY",
          "document_type": "ID_CARD",
      },
  )
  assert summary == "发起第三方实名认证 【user】（认证方式：人工审核，证件类型：身份证）失败"


def test_build_login_success():
  assert build_content("login", "auth", "登录", "user", True) == "账号 【user】登录成功"


def test_is_path_summary():
  assert is_path_summary("POST /api/v1/admin/sys/roles/create")
  assert not is_path_summary("账号 【user】登录成功")


def test_resolve_real_name_case_path():
  resource_type, action = resolve_audit_target("real-name/case", "init_third_party")
  assert resource_type == "real_name_case"
  assert action == "init_third_party"


def test_resolve_iam_role_path():
  resource_type, action = resolve_audit_target("sys/roles", "create")
  assert resource_type == "iam_role"
  assert action == "create"


def test_resolve_profile_password_update():
  resource_type, action = resolve_audit_target("profile/password", "update")
  assert resource_type == "profile_center"
  assert action == "update_password"
