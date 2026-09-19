"""审计分析查询仓储（供 analyzer 使用）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_po import SysOperationAuditLog


class AuditAnalysisRepositoryImpl:
    """审计日志分析 SQL 查询。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def count_since(self, since: datetime) -> int:
        volume = (
            await self.db.execute(
                select(func.count(SysOperationAuditLog.id)).where(
                    SysOperationAuditLog.created_at >= since
                )
            )
        ).scalar_one()
        return int(volume or 0)

    async def list_sensitive_actions_since(
        self, since: datetime, actions: tuple[str, ...]
    ) -> list[dict]:
        stmt = select(SysOperationAuditLog.action).where(
            SysOperationAuditLog.created_at >= since,
            SysOperationAuditLog.action.in_(actions),
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [{"action": action} for action in rows]

    async def count_sensitive_ops_by_account(
        self, since: datetime, actions: tuple[str, ...]
    ) -> list[dict]:
        stmt = (
            select(
                SysOperationAuditLog.account_id,
                func.count(SysOperationAuditLog.id).label("cnt"),
            )
            .where(
                SysOperationAuditLog.created_at >= since,
                SysOperationAuditLog.action.in_(actions),
                SysOperationAuditLog.account_id.isnot(None),
            )
            .group_by(SysOperationAuditLog.account_id)
        )
        rows = (await self.db.execute(stmt)).all()
        return [{"account_id": r.account_id, "count": int(r.cnt)} for r in rows]

    async def count_delete_ops_by_account(self, since: datetime, threshold: int) -> list[dict]:
        stmt = (
            select(
                SysOperationAuditLog.account_id,
                func.count(SysOperationAuditLog.id).label("cnt"),
            )
            .where(
                SysOperationAuditLog.created_at >= since,
                SysOperationAuditLog.action == "delete",
                SysOperationAuditLog.account_id.isnot(None),
            )
            .group_by(SysOperationAuditLog.account_id)
            .having(func.count(SysOperationAuditLog.id) >= threshold)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {"account_id": r.account_id, "count": int(r.cnt), "threshold": threshold} for r in rows
        ]

    async def count_login_ips_by_account(self, since: datetime, threshold: int) -> list[dict]:
        stmt = (
            select(
                SysOperationAuditLog.account_id,
                func.count(func.distinct(SysOperationAuditLog.ip)).label("ip_cnt"),
            )
            .where(
                SysOperationAuditLog.created_at >= since,
                SysOperationAuditLog.action == "login",
                SysOperationAuditLog.success == True,  # noqa: E712
                SysOperationAuditLog.account_id.isnot(None),
            )
            .group_by(SysOperationAuditLog.account_id)
            .having(func.count(func.distinct(SysOperationAuditLog.ip)) >= threshold)
        )
        rows = (await self.db.execute(stmt)).all()
        return [{"account_id": r.account_id, "ip_count": int(r.ip_cnt)} for r in rows]
