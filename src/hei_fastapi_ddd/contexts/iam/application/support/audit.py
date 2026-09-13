""" Author: Charlie

IAM 审计：将 ID / 授权结构解析为可读展示标签（对齐 hei-boot IamAuditLabelSupport）。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.account.query_service import AccountQueryService
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import AccountRepository
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.client_po import SysClientResource
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.dept_repository import DeptRepository
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.group_repository import GroupRepository
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_repository import RoleRepository


def permission_bind_field(
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


async def role_ids_field(db: AsyncSession, role_ids: Iterable[str]) -> dict[str, Any]:
    labels = await resolve_role_labels(db, role_ids)
    return {"角色": labels}


async def group_ids_field(db: AsyncSession, group_ids: Iterable[str]) -> dict[str, Any]:
    labels = await resolve_group_labels(db, group_ids)
    return {"用户组": labels}


async def account_ids_field(
    db: AsyncSession,
    account_ids: Iterable[str],
    *,
    account_type: str = "admin",
) -> dict[str, Any]:
    labels = await resolve_account_labels(db, account_ids, account_type=account_type)
    return {"账号": labels}


async def dept_grant_field(
    db: AsyncSession,
    grants: Sequence[Any],
) -> dict[str, Any]:
    return {"部门": await format_dept_grants(db, grants)}


async def grant_resource_field(
    db: AsyncSession,
    field_key: str,
    grants: Sequence[Any],
) -> dict[str, Any]:
    names = await _load_resource_names(db, _grant_resource_ids(grants))
    return {field_key: format_resource_grants(grants, names)}


async def grant_client_resource_field(
    db: AsyncSession,
    field_key: str,
    grants: Sequence[Any],
) -> dict[str, Any]:
    names = await _load_client_resource_names(db, _grant_resource_ids(grants))
    return {field_key: format_resource_grants(grants, names)}


def format_resource_grants(
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
        name = resource_names.get(resource_id, resource_id)
        keys = _grant_value(grant, "permission_keys", "permissionKeys") or []
        if isinstance(keys, str):
            keys = [keys]
        if keys:
            labels.append(f"{name}（{'，'.join(str(item) for item in keys)}）")
        else:
            labels.append(name)
    return labels


async def format_dept_grants(db: AsyncSession, grants: Sequence[Any]) -> list[str]:
    if not grants:
        return []
    dept_ids = [
        str(item)
        for item in (_grant_value(grant, "dept_id", "deptId") for grant in grants)
        if item
    ]
    dept_map = {
        dept.id: _default_name(dept.name, dept.id)
        for dept in await DeptRepository(db).list_by_ids(list(dict.fromkeys(dept_ids)))
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


async def resolve_role_labels(db: AsyncSession, role_ids: Iterable[str]) -> list[str]:
    unique = _distinct_ids(role_ids)
    if not unique:
        return []
    roles = await RoleRepository(db).list_by_ids(unique)
    label_map = {
        role.id: _default_name_with_code(role.name, role.code, role.id) for role in roles
    }
    return [label_map.get(role_id, role_id) for role_id in unique]


async def resolve_group_labels(db: AsyncSession, group_ids: Iterable[str]) -> list[str]:
    unique = _distinct_ids(group_ids)
    if not unique:
        return []
    groups = await GroupRepository(db).list_by_ids(unique)
    label_map = {group.id: _default_name(group.name, group.id) for group in groups}
    return [label_map.get(group_id, group_id) for group_id in unique]


async def resolve_account_labels(
    db: AsyncSession,
    account_ids: Iterable[str],
    *,
    account_type: str = "admin",
) -> list[str]:
    unique = _distinct_ids(account_ids)
    if not unique:
        return []
    accounts = await AccountRepository(db).list_accounts_by_ids(unique)
    schemas = await AccountQueryService(db).build_account_picker_schemas(accounts)
    label_map = {
        item.id: (item.account or item.nickname or item.id)
        for item in schemas
    }
    return [label_map.get(account_id, account_id) for account_id in unique]


async def _load_resource_names(db: AsyncSession, resource_ids: list[str]) -> dict[str, str]:
    if not resource_ids:
        return {}
    stmt = select(SysResource).where(SysResource.id.in_(resource_ids))
    rows = list((await db.execute(stmt)).scalars().all())
    return {
        row.id: _default_name_with_code(row.name, row.code, row.id)
        for row in rows
    }


async def _load_client_resource_names(
    db: AsyncSession,
    resource_ids: list[str],
) -> dict[str, str]:
    if not resource_ids:
        return {}
    stmt = select(SysClientResource).where(SysClientResource.id.in_(resource_ids))
    rows = list((await db.execute(stmt)).scalars().all())
    return {
        row.id: _default_name_with_code(row.name, row.code, row.id)
        for row in rows
    }


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
