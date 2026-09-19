"""workspace 仓储端口。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class WorkspaceShortcutRepository(Protocol):
    async def list_by_account(self, account_id: str) -> list[dict[str, Any]]: ...
    async def replace_for_account(
        self, account_id: str, rows: Sequence[Mapping[str, Any]]
    ) -> None: ...
