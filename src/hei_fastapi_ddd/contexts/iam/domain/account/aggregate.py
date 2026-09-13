""" Author: Charlie

账户聚合根：状态流转与注销不变量。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from hei_fastapi_ddd.contexts.iam.domain.account.events import (
    AccountDeleted,
    AuthorizationChanged,
)
from hei_fastapi_ddd.ddd_kernel.domain_exception import DomainException
from hei_fastapi_ddd.ddd_kernel.entity import AggregateRoot

_STATUS_ENABLED = "ENABLED"
_STATUS_DISABLED = "DISABLED"
_STATUS_CANCELLED = "CANCELLED"
_ALLOWED_ACTIVE = frozenset({_STATUS_ENABLED, _STATUS_DISABLED})


@dataclass
class Account(AggregateRoot[str]):
    """账户聚合：维护状态、注销与授权变更事件。"""

    id: str
    account_type: str
    account_status: str = _STATUS_ENABLED
    password_hash: str = ""
    cancelled_at: datetime | None = None
    cancelled_by: str | None = None
    cancel_reason: str | None = None
    cancel_notify_email: str | None = None
    cancel_notify_phone: str | None = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self, self.id)

    def ensure_not_cancelled(self) -> None:
        """已注销账户禁止管理端变更。"""
        if self.account_status == _STATUS_CANCELLED or self.cancelled_at is not None:
            raise DomainException("已注销账号不允许通过管理端修改")

    def change_status(self, new_status: str) -> None:
        """变更启用/停用状态；不可从注销态回退。"""
        # 1. 注销态不可再改状态
        self.ensure_not_cancelled()
        # 2. 仅允许 ENABLED/DISABLED
        value = (new_status or "").strip().upper()
        if value not in _ALLOWED_ACTIVE:
            raise DomainException(f"Invalid account status: {new_status}")
        # 3. 写入
        self.account_status = value

    def cancel(
        self,
        *,
        reason: str | None,
        cancelled_by: str | None,
        notify_email: str | None,
        notify_phone: str | None,
        password_hash: str,
    ) -> None:
        """注销账户：标记状态、快照联系方式并轮换密码哈希。"""
        # 1. 幂等：已注销直接返回
        if self.account_status == _STATUS_CANCELLED:
            return
        # 2. 写入注销元数据
        self.account_status = _STATUS_CANCELLED
        self.cancelled_at = self.cancelled_at or datetime.now(UTC)
        self.cancelled_by = cancelled_by
        self.cancel_reason = reason
        self.cancel_notify_email = notify_email
        self.cancel_notify_phone = notify_phone
        # 3. 失效凭据
        self.password_hash = password_hash

    def mark_authorization_changed(self, change_type: str) -> None:
        """记录授权变更领域事件。"""
        self.add_domain_event(
            AuthorizationChanged(
                aggregate_id=self.id,
                account_id=self.id,
                change_type=change_type,
            )
        )

    def mark_deleted(self) -> None:
        """记录账户删除领域事件。"""
        self.add_domain_event(
            AccountDeleted(
                aggregate_id=self.id,
                account_id=self.id,
                account_type=self.account_type,
            )
        )
