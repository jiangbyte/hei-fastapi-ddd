"""Author: Charlie

IAM 组织只读 API：供 profile 等上下文批量解析角色/部门/群组名称。
"""

from __future__ import annotations

from typing import Any, Protocol


class IamOrgReadApi(Protocol):
    """跨上下文组织名称解析端口。"""

    async def list_role_names_by_ids(self, role_ids: list[str]) -> dict[str, str]:
        """角色 ID → 名称。"""
        ...

    async def list_dept_names_by_ids(self, dept_ids: list[str]) -> dict[str, str]:
        """部门 ID → 名称。"""
        ...

    async def list_group_names_by_ids(self, group_ids: list[str]) -> dict[str, str]:
        """群组 ID → 名称。"""
        ...

    async def list_id_name_rows(
        self,
        role_ids: list[str],
        dept_ids: list[str],
        group_ids: list[str],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """按 ID 顺序返回 id/name 行（无映射时 name 为 None）。"""
        ...
