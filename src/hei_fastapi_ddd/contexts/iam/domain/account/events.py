""" Author: Charlie

账户领域事件。
"""

from __future__ import annotations

from dataclasses import dataclass

from hei_fastapi_ddd.ddd_kernel.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class AuthorizationChanged(DomainEvent):
    """账户授权（角色/资源/部门/分组）发生变更。"""

    account_id: str
    change_type: str


@dataclass(frozen=True, kw_only=True)
class AccountDeleted(DomainEvent):
    """账户被删除。"""

    account_id: str
    account_type: str
