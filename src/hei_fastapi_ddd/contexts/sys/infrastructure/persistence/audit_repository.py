""" Author: Charlie

操作审计日志仓储层：封装审计记录的持久化与后台分页查询。
"""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, inspect, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_po import SysOperationAuditLog
from hei_fastapi_ddd.types.business import NotFoundError


def _row(entity: SysOperationAuditLog) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class OperationAuditRepositoryImpl:
    """操作审计日志仓储，提供创建、单条查询与后台分页。"""

    def __init__(self, db: AsyncSession) -> None:
        """绑定数据库会话。"""
        self.db = db

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """写入一条审计日志并 flush，返回持久化实体。"""
        entity = SysOperationAuditLog(**dict(data))
        self.db.add(entity)
        await self.db.flush()
        return _row(entity)

    async def get_required(self, audit_id: str) -> dict[str, Any]:
        """按主键查询审计日志，不存在时抛出 NotFoundError。"""
        entity = await self.db.get(SysOperationAuditLog, audit_id)
        if entity is None:
            raise NotFoundError("Operation audit log not found")
        return _row(entity)

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """按查询条件后台分页，返回记录列表与总数。"""
        stmt = select(SysOperationAuditLog)
        count_stmt = select(func.count(SysOperationAuditLog.id))
        filters = []
        if filters.get("module"):
            filters.append(SysOperationAuditLog.module == filters["module"])
        if filters.get("action"):
            filters.append(SysOperationAuditLog.action == filters["action"])
        elif filters.get("exclude_action"):
            filters.append(SysOperationAuditLog.action != filters["exclude_action"])
        if filters.get("account_id"):
            filters.append(SysOperationAuditLog.account_id == filters["account_id"])
        if filters.get("success") is not None:
            filters.append(SysOperationAuditLog.success.is_(filters["success"]))
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysOperationAuditLog.created_at.desc(), SysOperationAuditLog.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return [_row(i) for i in items], total

    async def cleanup_expired_login_logs(self, *, retention_days: int, batch_size: int) -> int:
        """按保留天数分批删除 login/logout 审计日志。"""
        return await self._cleanup_expired(retention_days=retention_days, batch_size=batch_size, login_logs=True)

    async def cleanup_expired_operation_logs(self, *, retention_days: int, batch_size: int) -> int:
        """按保留天数分批删除非 login/logout 操作审计日志。"""
        return await self._cleanup_expired(retention_days=retention_days, batch_size=batch_size, login_logs=False)

    async def _cleanup_expired(self, *, retention_days: int, batch_size: int, login_logs: bool) -> int:
        if retention_days <= 0:
            return 0
        limit = max(1, batch_size or 1000)
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        total_deleted = 0
        max_rounds = 100
        for _ in range(max_rounds):
            filters = [SysOperationAuditLog.created_at < cutoff]
            if login_logs:
                filters.append(SysOperationAuditLog.action.in_(("login", "logout")))
            else:
                filters.append(
                    or_(
                        SysOperationAuditLog.action.is_(None),
                        SysOperationAuditLog.action.notin_(("login", "logout")),
                    )
                )
            ids_stmt = (
                select(SysOperationAuditLog.id)
                .where(*filters)
                .order_by(SysOperationAuditLog.created_at.asc())
                .limit(limit)
            )
            ids = list((await self.db.execute(ids_stmt)).scalars().all())
            if not ids:
                break
            result = await self.db.execute(
                delete(SysOperationAuditLog).where(SysOperationAuditLog.id.in_(ids))
            )
            deleted = int(result.rowcount or 0)
            total_deleted += deleted
            await self.db.flush()
            if deleted < limit:
                break
        return total_deleted
