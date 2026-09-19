"""Author: Charlie

账户密码策略端口。
"""

from __future__ import annotations

from typing import Protocol


class AccountPasswordPort(Protocol):
    """密码历史与策略相关持久化。"""

    async def list_recent_hashes(self, account_id: str, limit: int) -> list[str]:
        ...

    async def append(
        self,
        account_id: str,
        plain_password: str,
        *,
        changed_by: str | None,
        change_reason: str | None,
    ) -> None:
        ...

    async def get_latest_changed_at(self, account_id: str):
        ...

    async def matches_any_history(self, account_id: str, plain_password: str, limit: int) -> bool:
        ...
