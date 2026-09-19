"""工作台应用服务。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.workspace.dto import WorkspaceShortcutSaveCommand
from hei_fastapi_ddd.contexts.sys.domain.workspace.read_port import WorkspaceReadPort
from hei_fastapi_ddd.contexts.sys.domain.workspace.repository import WorkspaceShortcutRepository
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.types.business import BusinessError

MAX_SHORTCUTS = 16
HOME_CODE = "sys-workspace"
ACTIVITY_LIMIT = 10


class WorkspaceService:
    def __init__(
        self,
        db: AsyncSession,
        shortcut_repo: WorkspaceShortcutRepository,
        read_port: WorkspaceReadPort,
    ):
        self.db = db
        self.shortcut_repo = shortcut_repo
        self.read_port = read_port

    async def overview(self, session: SessionPayload) -> dict:
        return {
            "shortcuts": await self.list_shortcuts(session),
            "recent_operations": await self.read_port.list_recent_activities(
                session.account_id, login_only=False, exclude_login=True, limit=ACTIVITY_LIMIT
            ),
            "recent_logins": await self.read_port.list_recent_activities(
                session.account_id, login_only=True, exclude_login=False, limit=ACTIVITY_LIMIT
            ),
        }

    async def list_shortcuts(self, session: SessionPayload) -> list[dict]:
        rows = await self.shortcut_repo.list_by_account(session.account_id)
        if not rows:
            return []
        resource_ids = list(dict.fromkeys(r["resource_id"] for r in rows if r.get("resource_id")))
        menus = await self.read_port.load_menus(resource_ids)
        granted = await self._resolve_granted_resource_ids(session)
        results: list[dict] = []
        for row in rows:
            menu = menus.get(str(row.get("resource_id")))
            if menu is None or not menu.get("path"):
                continue
            if granted is not None and str(row.get("resource_id")) not in granted:
                continue
            results.append(
                {
                    "id": row.get("id"),
                    "resource_id": row.get("resource_id"),
                    "sort": row.get("sort"),
                    "name": menu.get("name"),
                    "path": menu.get("path"),
                    "icon": menu.get("icon"),
                    "code": menu.get("code"),
                }
            )
        return results

    async def replace_shortcuts(
        self, session: SessionPayload, command: WorkspaceShortcutSaveCommand
    ) -> list[dict]:
        normalized = self._normalize_resource_ids(command.resource_ids)
        if len(normalized) > MAX_SHORTCUTS:
            raise BusinessError(f"快捷应用最多 {MAX_SHORTCUTS} 个")
        granted = await self._resolve_granted_resource_ids(session)
        menus = await self.read_port.load_menus(normalized)
        rows: list[dict] = []
        sort = 1
        for resource_id in normalized:
            menu = menus.get(resource_id)
            if (
                menu is None
                or not menu.get("path")
                or menu.get("code") == HOME_CODE
            ):
                raise BusinessError("存在不可用的菜单资源")
            if granted is not None and resource_id not in granted:
                raise BusinessError(f"存在未授权的菜单：{menu.get('name')}")
            rows.append(
                {
                    "account_id": session.account_id,
                    "resource_id": resource_id,
                    "sort": sort,
                    "created_by": session.account_id,
                    "updated_by": session.account_id,
                }
            )
            sort += 1
        audit_snapshots.subject(session.account_id)
        async with transactional(self.db):
            await self.shortcut_repo.replace_for_account(session.account_id, rows)
        audit_snapshots.after({"resourceIds": normalized})
        return await self.list_shortcuts(session)

    async def _resolve_granted_resource_ids(self, session: SessionPayload) -> set[str] | None:
        if await self._is_full_access(session):
            return None
        return set(session.resource_ids or [])

    async def _is_full_access(self, session: SessionPayload) -> bool:
        if "*:*:*" in set(session.permission_keys or []):
            return True
        return await self.read_port.has_super_admin_role(list(session.role_ids or []))

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
