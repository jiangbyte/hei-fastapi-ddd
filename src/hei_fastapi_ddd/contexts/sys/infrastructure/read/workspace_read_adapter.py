"""工作台跨表只读查询适配。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.domain.role.constants import SUPER_ADMIN_ROLE_CODE
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po import SysRole
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_po import SysOperationAuditLog


class WorkspaceReadAdapter:
    """IAM 菜单/角色与审计活动只读查询。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_menus(self, resource_ids: list[str]) -> dict[str, dict]:
        if not resource_ids:
            return {}
        stmt = select(SysResource).where(
            SysResource.id.in_(resource_ids),
            SysResource.resource_type == "MENU",
            SysResource.status == "ENABLED",
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        return {
            item.id: {
                "id": item.id,
                "name": item.name,
                "path": item.path,
                "icon": item.icon,
                "code": item.code,
            }
            for item in items
        }

    async def has_super_admin_role(self, role_ids: list[str]) -> bool:
        if not role_ids:
            return False
        stmt = (
            select(SysRole.id)
            .where(SysRole.id.in_(role_ids), SysRole.code == SUPER_ADMIN_ROLE_CODE)
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def list_recent_activities(
        self, account_id: str, *, login_only: bool, exclude_login: bool, limit: int
    ) -> list[dict]:
        stmt = (
            select(SysOperationAuditLog)
            .where(SysOperationAuditLog.account_id == account_id)
            .order_by(SysOperationAuditLog.created_at.desc())
            .limit(limit)
        )
        if login_only:
            stmt = stmt.where(SysOperationAuditLog.action == "login")
        elif exclude_login:
            stmt = stmt.where(
                (SysOperationAuditLog.action != "login") | (SysOperationAuditLog.action.is_(None))
            )
        rows = list((await self.db.execute(stmt)).scalars().all())
        return [
            {
                "id": row.id,
                "module": row.module,
                "action": row.action,
                "summary": row.summary,
                "created_at": row.created_at,
            }
            for row in rows
        ]
