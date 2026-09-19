"""Author: Charlie

IAM 审计标签适配器：实现 application 端口，依赖基础设施仓储。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.support.audit_port import IamAuditPort
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import (
    AccountRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.client_po import SysClientResource
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.dept_repository import (
    DeptRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.group_repository import (
    GroupRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_repository import (
    RoleRepositoryImpl,
)


class IamAuditAdapter:
    """IAM 审计可读标签。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._accounts = AccountRepositoryImpl(db)
        self._depts = DeptRepositoryImpl(db)
        self._roles = RoleRepositoryImpl(db)
        self._groups = GroupRepositoryImpl(db)

    def permission_bind_field(
        self,
        permission_key: str | None,
        account_type: str | None,
        data_scope: str | None,
    ) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        if permission_key and str(permission_key).strip():
            fields["权限键"] = str(permission_key).strip()
        if account_type and str(account_type).strip():
            fields["账号类型"] = str(account_type).strip()
        if data_scope and str(data_scope).strip():
            fields["数据范围"] = str(data_scope).strip()
        return fields

    async def role_ids_field(self, role_ids: Iterable[str]) -> dict[str, Any]:
        return {"角色": await self._resolve_role_labels(role_ids)}

    async def group_ids_field(self, group_ids: Iterable[str]) -> dict[str, Any]:
        return {"用户组": await self._resolve_group_labels(group_ids)}

    async def account_ids_field(
        self,
        account_ids: Iterable[str],
        *,
        account_type: str = "admin",
    ) -> dict[str, Any]:
        _ = account_type
        return {"账号": await self._resolve_account_labels(account_ids)}

    async def dept_grant_field(self, grants: Sequence[Any]) -> dict[str, Any]:
        return {"部门": await self._format_dept_grants(grants)}

    async def grant_resource_field(
        self,
        field_key: str,
        grants: Sequence[Any],
    ) -> dict[str, Any]:
        names = await self._load_resource_names(_grant_resource_ids(grants))
        return {field_key: _format_resource_grants(grants, names)}

    async def grant_client_resource_field(
        self,
        field_key: str,
        grants: Sequence[Any],
    ) -> dict[str, Any]:
        names = await self._load_client_resource_names(_grant_resource_ids(grants))
        return {field_key: _format_resource_grants(grants, names)}

    async def _resolve_role_labels(self, role_ids: Iterable[str]) -> list[str]:
        unique = _distinct_ids(role_ids)
        if not unique:
            return []
        roles = await self._roles.list_by_ids(unique)
        label_map = {
            str(row["id"]): _default_name_with_code(
                row.get("name"), row.get("code"), str(row["id"])
            )
            for row in roles
        }
        return [label_map.get(role_id, role_id) for role_id in unique]

    async def _resolve_group_labels(self, group_ids: Iterable[str]) -> list[str]:
        unique = _distinct_ids(group_ids)
        if not unique:
            return []
        groups = await self._groups.list_by_ids(unique)
        label_map = {
            str(row["id"]): _default_name(row.get("name"), str(row["id"])) for row in groups
        }
        return [label_map.get(group_id, group_id) for group_id in unique]

    async def _resolve_account_labels(self, account_ids: Iterable[str]) -> list[str]:
        unique = _distinct_ids(account_ids)
        if not unique:
            return []
        accounts = await self._accounts.list_accounts_by_ids(unique)
        identities = await self._accounts.list_identities_by_account_ids(unique)
        identity_map: dict[str, list[dict[str, Any]]] = {}
        for item in identities:
            identity_map.setdefault(str(item["account_id"]), []).append(item)
        labels: list[str] = []
        for account in accounts:
            account_id = str(account["id"])
            idents = identity_map.get(account_id, [])
            primary = next(
                (i for i in idents if i.get("identity_type") == "ACCOUNT" and i.get("is_primary")),
                None,
            ) or next((i for i in idents if i.get("identity_type") == "ACCOUNT"), None)
            label = (primary or {}).get("identifier") or account_id
            labels.append(str(label))
        label_by_id = {str(a["id"]): labels[idx] for idx, a in enumerate(accounts)}
        return [label_by_id.get(aid, aid) for aid in unique]

    async def _format_dept_grants(self, grants: Sequence[Any]) -> list[str]:
        if not grants:
            return []
        dept_ids = [
            str(item)
            for item in (_grant_value(grant, "dept_id", "deptId") for grant in grants)
            if item
        ]
        dept_rows = await self._depts.list_by_ids(list(dict.fromkeys(dept_ids)))
        dept_map = {
            str(row["id"]): _default_name(row.get("name"), str(row["id"])) for row in dept_rows
        }
        labels: list[str] = []
        for grant in grants:
            dept_id = _grant_value(grant, "dept_id", "deptId")
            if not dept_id:
                continue
            name = dept_map.get(str(dept_id), str(dept_id))
            is_primary = _grant_value(grant, "is_primary", "isPrimary")
            if is_primary in (True, "true", "1", 1, "Y", "y"):
                labels.append(f"{name}（主部门）")
            else:
                labels.append(name)
        return labels

    async def _load_resource_names(self, resource_ids: list[str]) -> dict[str, str]:
        if not resource_ids:
            return {}
        stmt = select(SysResource).where(SysResource.id.in_(resource_ids))
        rows = list((await self.db.execute(stmt)).scalars().all())
        return {
            row.id: _default_name_with_code(row.name, row.code, row.id)
            for row in rows
        }

    async def _load_client_resource_names(self, resource_ids: list[str]) -> dict[str, str]:
        if not resource_ids:
            return {}
        stmt = select(SysClientResource).where(SysClientResource.id.in_(resource_ids))
        rows = list((await self.db.execute(stmt)).scalars().all())
        return {
            row.id: _default_name_with_code(row.name, row.code, row.id)
            for row in rows
        }


def get_iam_audit_port(db: AsyncSession) -> IamAuditPort:
    return IamAuditAdapter(db)


def _format_resource_grants(
    grants: Sequence[Any],
    resource_names: Mapping[str, str],
) -> list[str]:
    if not grants:
        return []
    labels: list[str] = []
    for grant in grants:
        resource_id = _grant_value(grant, "resource_id", "resourceId")
        if not resource_id:
            continue
        name = resource_names.get(str(resource_id), str(resource_id))
        keys = _grant_value(grant, "permission_keys", "permissionKeys") or []
        if isinstance(keys, str):
            keys = [keys]
        if keys:
            labels.append(f"{name}（{'，'.join(str(item) for item in keys)}）")
        else:
            labels.append(name)
    return labels


def _grant_resource_ids(grants: Sequence[Any]) -> list[str]:
    return list(
        dict.fromkeys(
            str(item)
            for item in (_grant_value(grant, "resource_id", "resourceId") for grant in grants)
            if item
        )
    )


def _grant_value(grant: Any, *keys: str) -> Any:
    if grant is None:
        return None
    if isinstance(grant, Mapping):
        for key in keys:
            if key in grant:
                return grant[key]
        return None
    for key in keys:
        if hasattr(grant, key):
            return getattr(grant, key)
    return None


def _distinct_ids(ids: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in ids if item and str(item).strip()))


def _default_name(name: str | None, fallback: str) -> str:
    if name and str(name).strip():
        return str(name).strip()
    return fallback


def _default_name_with_code(name: str | None, code: str | None, fallback: str) -> str:
    if name and str(name).strip():
        return str(name).strip()
    if code and str(code).strip():
        return str(code).strip()
    return fallback
