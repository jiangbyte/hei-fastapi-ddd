""" Author: Charlie """

from hei_fastapi_ddd.shared.audit.skip_catalog import should_skip_audit


def test_should_skip_audit_profile_avatar() -> None:
    assert should_skip_audit("profile_center", "upload_avatar") is True
    assert should_skip_audit("profile-center", "upload-avatar") is True


def test_should_skip_audit_notice_read() -> None:
    assert should_skip_audit("sys_notice", "read") is True
    assert should_skip_audit("sys_notice", "read_all") is True


def test_should_skip_audit_normal_mutations() -> None:
    assert should_skip_audit("sys_banner", "create") is False
    assert should_skip_audit("iam_account", "update") is False
