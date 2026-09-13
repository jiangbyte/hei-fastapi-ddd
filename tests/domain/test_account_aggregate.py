"""账户聚合领域单测。"""

from __future__ import annotations

import pytest

from hei_fastapi_ddd.contexts.iam.domain.account.aggregate import Account
from hei_fastapi_ddd.contexts.iam.domain.account.events import AccountDeleted, AuthorizationChanged
from hei_fastapi_ddd.ddd_kernel.domain_exception import DomainException


def test_cancel_account_sets_status_and_rotates_password() -> None:
    """注销应写入 CANCELLED 并轮换密码哈希。"""
    # 1. 构造启用态账户
    account = Account(id="1", account_type="ADMIN", account_status="ENABLED", password_hash="old")
    # 2. 执行注销
    account.cancel(
        reason="user request",
        cancelled_by="admin",
        notify_email="a@b.c",
        notify_phone=None,
        password_hash="rotated",
    )
    # 3. 断言状态与凭据
    assert account.account_status == "CANCELLED"
    assert account.password_hash == "rotated"
    assert account.cancel_notify_email == "a@b.c"


def test_change_status_rejects_cancelled() -> None:
    """已注销账户禁止再改状态。"""
    account = Account(id="1", account_type="ADMIN", account_status="CANCELLED")
    with pytest.raises(DomainException):
        account.change_status("ENABLED")


def test_mark_deleted_emits_event() -> None:
    """删除标记应产出 AccountDeleted 事件。"""
    account = Account(id="9", account_type="PORTAL", account_status="ENABLED")
    account.mark_deleted()
    events = account.pull_domain_events()
    assert len(events) == 1
    assert isinstance(events[0], AccountDeleted)
    assert events[0].account_id == "9"


def test_authorization_changed_event() -> None:
    """授权变更应产出 AuthorizationChanged 事件。"""
    account = Account(id="3", account_type="ADMIN", account_status="ENABLED")
    account.mark_authorization_changed("role")
    events = account.pull_domain_events()
    assert isinstance(events[0], AuthorizationChanged)
    assert events[0].change_type == "role"
