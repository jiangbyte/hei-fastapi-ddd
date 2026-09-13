""" Author: Charlie

工作台快捷应用仓储。
"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.workspace_po import (
    SysWorkspaceShortcut,
)


class WorkspaceShortcutRepository:
    """个人快捷应用 CRUD。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_account(self, account_id: str) -> list[SysWorkspaceShortcut]:
        stmt = (
            select(SysWorkspaceShortcut)
            .where(SysWorkspaceShortcut.account_id == account_id)
            .order_by(SysWorkspaceShortcut.sort.asc(), SysWorkspaceShortcut.id.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def replace_for_account(
        self, account_id: str, rows: list[SysWorkspaceShortcut]
    ) -> None:
        await self.db.execute(
            delete(SysWorkspaceShortcut).where(SysWorkspaceShortcut.account_id == account_id)
        )
        for row in rows:
            self.db.add(row)
        await self.db.flush()
