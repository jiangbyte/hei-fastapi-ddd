"""Author: Charlie

IamOrgReadApi 适配器：委托 IAM 基础设施仓储批量解析名称。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.api.org_read_api import IamOrgReadApi
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.dept_repository import (
    DeptRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.group_repository import (
    GroupRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_repository import (
    RoleRepositoryImpl,
)


def _ordered_id_names(ids: list[str], name_map: dict[str, str]) -> list[dict[str, Any]]:
    return [{"id": item_id, "name": name_map.get(item_id)} for item_id in ids]


class IamOrgReadAdapter:
    """组织只读端口实现。"""

    def __init__(self, db: AsyncSession):
        self._roles = RoleRepositoryImpl(db)
        self._depts = DeptRepositoryImpl(db)
        self._groups = GroupRepositoryImpl(db)

    async def list_role_names_by_ids(self, role_ids: list[str]) -> dict[str, str]:
        roles = await self._roles.list_by_ids(role_ids)
        return {item.id: item.name for item in roles}

    async def list_dept_names_by_ids(self, dept_ids: list[str]) -> dict[str, str]:
        depts = await self._depts.list_by_ids(dept_ids)
        return {str(item["id"]): str(item.get("name") or "") for item in depts}

    async def list_group_names_by_ids(self, group_ids: list[str]) -> dict[str, str]:
        groups = await self._groups.list_by_ids(group_ids)
        return {item.id: item.name for item in groups}

    async def list_id_name_rows(
        self,
        role_ids: list[str],
        dept_ids: list[str],
        group_ids: list[str],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        role_map = await self.list_role_names_by_ids(role_ids)
        dept_map = await self.list_dept_names_by_ids(dept_ids)
        group_map = await self.list_group_names_by_ids(group_ids)
        return (
            _ordered_id_names(role_ids, role_map),
            _ordered_id_names(dept_ids, dept_map),
            _ordered_id_names(group_ids, group_map),
        )


def get_iam_org_read_api(db: AsyncSession) -> IamOrgReadApi:
    return IamOrgReadAdapter(db)
