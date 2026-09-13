""" Author: Charlie

工作台服务：快捷应用与总览（对齐 hei-boot WorkspaceServiceImpl）。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.domain.role.constants import SUPER_ADMIN_ROLE_CODE
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po import SysRole
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_po import SysOperationAuditLog
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.workspace_po import (
    SysWorkspaceShortcut,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.workspace_repository import (
    WorkspaceShortcutRepository,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.workspace_schemas import (
    WorkspaceActivityItem,
    WorkspaceOverviewResponse,
    WorkspaceShortcutResult,
    WorkspaceShortcutSaveRequest,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import to_schema_list
from hei_fastapi_ddd.shared.security.session import SessionPayload

MAX_SHORTCUTS = 16
HOME_CODE = "sys-workspace"
ACTIVITY_LIMIT = 10


class WorkspaceService:
    """工作台业务逻辑。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.shortcut_repo = WorkspaceShortcutRepository(db)

    async def overview(self, session: SessionPayload) -> WorkspaceOverviewResponse:
        shortcuts = await self.list_shortcuts(session)
        recent_operations = await self._list_recent_activities(
            session.account_id, login_only=False, exclude_login=True
        )
        recent_logins = await self._list_recent_activities(
            session.account_id, login_only=True
        )
        return WorkspaceOverviewResponse(
            shortcuts=shortcuts,
            recent_operations=recent_operations,
            recent_logins=recent_logins,
        )

    async def list_shortcuts(self, session: SessionPayload) -> list[WorkspaceShortcutResult]:
        rows = await self.shortcut_repo.list_by_account(session.account_id)
        if not rows:
            return []
        resource_ids = list(dict.fromkeys(r.resource_id for r in rows if r.resource_id))
        menus = await self._load_menus(resource_ids)
        granted = await self._resolve_granted_resource_ids(session)
        results: list[WorkspaceShortcutResult] = []
        for row in rows:
            menu = menus.get(row.resource_id)
            if menu is None or not menu.path:
                continue
            if granted is not None and row.resource_id not in granted:
                continue
            results.append(
                WorkspaceShortcutResult(
                    id=row.id,
                    resource_id=row.resource_id,
                    sort=row.sort,
                    name=menu.name,
                    path=menu.path,
                    icon=menu.icon,
                    code=menu.code,
                )
            )
        return results

    async def replace_shortcuts(
        self, session: SessionPayload, payload: WorkspaceShortcutSaveRequest
    ) -> list[WorkspaceShortcutResult]:
        normalized = self._normalize_resource_ids(payload.resource_ids)
        if len(normalized) > MAX_SHORTCUTS:
            raise BusinessError(f"快捷应用最多 {MAX_SHORTCUTS} 个")
        granted = await self._resolve_granted_resource_ids(session)
        entities: list[SysWorkspaceShortcut] = []
        sort = 1
        for resource_id in normalized:
            menu = await self.db.get(SysResource, resource_id)
            if (
                menu is None
                or menu.resource_type != "MENU"
                or menu.status != "ENABLED"
                or not menu.path
                or menu.code == HOME_CODE
            ):
                raise BusinessError("存在不可用的菜单资源")
            if granted is not None and resource_id not in granted:
                raise BusinessError(f"存在未授权的菜单：{menu.name}")
            entities.append(
                SysWorkspaceShortcut(
                    account_id=session.account_id,
                    resource_id=resource_id,
                    sort=sort,
                    created_by=session.account_id,
                    updated_by=session.account_id,
                )
            )
            sort += 1
        audit_snapshots.subject(session.account_id)
        async with transactional(self.db):
            await self.shortcut_repo.replace_for_account(session.account_id, entities)
        audit_snapshots.after({"resourceIds": normalized})
        return await self.list_shortcuts(session)

    async def _load_menus(self, resource_ids: list[str]) -> dict[str, SysResource]:
        if not resource_ids:
            return {}
        stmt = select(SysResource).where(
            SysResource.id.in_(resource_ids),
            SysResource.resource_type == "MENU",
            SysResource.status == "ENABLED",
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        return {item.id: item for item in items}

    async def _resolve_granted_resource_ids(self, session: SessionPayload) -> set[str] | None:
        if await self._is_full_access(session):
            return None
        return set(session.resource_ids or [])

    async def _is_full_access(self, session: SessionPayload) -> bool:
        if "*:*:*" in set(session.permission_keys or []):
            return True
        role_ids = list(session.role_ids or [])
        if not role_ids:
            return False
        stmt = (
            select(SysRole.id)
            .where(SysRole.id.in_(role_ids), SysRole.code == SUPER_ADMIN_ROLE_CODE)
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    @staticmethod
    def _normalize_resource_ids(resource_ids: list[str] | None) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for raw in resource_ids or []:
            item = str(raw or "").strip()
            if item and item not in seen:
                seen.add(item)
                unique.append(item)
        return unique

    async def _list_recent_activities(
        self, account_id: str, *, login_only: bool, exclude_login: bool = False
    ) -> list[WorkspaceActivityItem]:
        stmt = (
            select(SysOperationAuditLog)
            .where(SysOperationAuditLog.account_id == account_id)
            .order_by(SysOperationAuditLog.created_at.desc())
            .limit(ACTIVITY_LIMIT)
        )
        if login_only:
            stmt = stmt.where(SysOperationAuditLog.action == "login")
        elif exclude_login:
            stmt = stmt.where(
                (SysOperationAuditLog.action != "login") | (SysOperationAuditLog.action.is_(None))
            )
        rows = list((await self.db.execute(stmt)).scalars().all())
        return to_schema_list(WorkspaceActivityItem, rows)
