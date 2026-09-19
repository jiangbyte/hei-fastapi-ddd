"""工作台快捷应用仓储实现。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import delete, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.workspace_po import (
    SysWorkspaceShortcut,
)


def _row(entity: SysWorkspaceShortcut) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class WorkspaceShortcutRepositoryImpl:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_account(self, account_id: str) -> list[dict[str, Any]]:
        stmt = (
            select(SysWorkspaceShortcut)
            .where(SysWorkspaceShortcut.account_id == account_id)
            .order_by(SysWorkspaceShortcut.sort.asc(), SysWorkspaceShortcut.id.asc())
        )
        return [_row(r) for r in (await self.db.execute(stmt)).scalars().all()]

    async def replace_for_account(
        self, account_id: str, rows: Sequence[Mapping[str, Any]]
    ) -> None:
        await self.db.execute(
            delete(SysWorkspaceShortcut).where(SysWorkspaceShortcut.account_id == account_id)
        )
        for row in rows:
            self.db.add(SysWorkspaceShortcut(**dict(row)))
        await self.db.flush()
