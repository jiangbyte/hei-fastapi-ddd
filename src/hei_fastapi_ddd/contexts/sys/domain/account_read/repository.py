"""跨 BC 账户标识只读端口（sys 应用层使用）。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class AccountIdentityReadPort(Protocol):
    """按账户 ID 查询登录标识。"""

    async def list_identities_by_account_ids(
        self, account_ids: list[str]
    ) -> list[Mapping[str, Any]]:
        ...
