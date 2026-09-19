"""Author: Charlie

客户端模块/资源应用服务：依赖 domain 仓储端口。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.support.audit_port import IamAuditPort
from hei_fastapi_ddd.contexts.iam.domain.client.repository import (
    ClientModuleRepository,
    ClientResourceRepository,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.permission_registry import ensure_registered_permission_key
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page

class ClientModuleService:
    """客户端模块应用服务。"""

    def __init__(self, db: AsyncSession, audit: IamAuditPort, *, repo: ClientModuleRepository):
        self.db = db
        self.audit = audit
        self.repo = repo

    async def create(self, payload: Mapping[str, Any]) -> None:
        """创建客户端模块。"""
        entity: dict[str, Any] | None = None
        async with transactional(self.db):
            entity = await self.repo.create(payload)
        if entity is not None:
            audit_snapshots.created_entity(entity)

    async def update(self, payload: Mapping[str, Any]) -> None:
        """更新客户端模块。"""
        existing = await self.repo.get_required(payload["id"])
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
        updated = await self.repo.get_required(payload["id"])
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest) -> None:
        """批量删除客户端模块。"""
        entities = await self.repo.list_by_ids(list(dict.fromkeys(payload.ids)))
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(self, query: IdQuery) -> dict:
        """查询客户端模块详情并回显创建人/更新人昵称。"""
        return await self.repo.get_required(query.id)

    async def page_admin(
        self,
        query: Mapping[str, Any],
    ) -> PageData[dict]:
        """分页查询客户端模块。"""
        items, total = await self.repo.page_admin(query)
        return build_page(query, total, items)

    async def selector(
        self,
        query: Mapping[str, Any],
    ) -> list[dict]:
        """返回启用的客户端模块（对齐 hei-boot 全字段 selector）。"""
        return await self.repo.list_enabled(query["account_type"])


class ClientResourceService:
    """客户端资源应用服务，负责资源 CRUD、树组装与权限绑定。"""

    def __init__(self, db: AsyncSession, audit: IamAuditPort, *, repo: ClientResourceRepository):
        self.db = db
        self.audit = audit
        self.repo = repo

    async def create(self, payload: Mapping[str, Any]) -> None:
        """创建客户端资源。"""
        entity: dict[str, Any] | None = None
        async with transactional(self.db):
            entity = await self.repo.create(payload)
        if entity is not None:
            audit_snapshots.created_entity(entity)

    async def update(self, payload: Mapping[str, Any]) -> None:
        """更新客户端资源。"""
        existing = await self.repo.get_required(payload["id"])
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
        updated = await self.repo.get_required(payload["id"])
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest) -> None:
        """批量删除客户端资源。"""
        entities = await self.repo.list_by_ids(list(dict.fromkeys(payload.ids)))
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(self, query: IdQuery) -> dict:
        """查询客户端资源详情，填充模块元信息与创建人昵称。"""
        entity = await self.repo.get_required(query.id)
        rows = await self._fill_module_meta_rows([entity], include_account_type=True)
        return rows[0]

    async def page_admin(
        self,
        query: Mapping[str, Any],
    ) -> PageData[dict]:
        """分页查询客户端资源。"""
        items, total = await self.repo.page_admin(query)
        enriched = await self._fill_module_meta_rows(items)
        return build_page(query, total, enriched)

    async def list_tree(
        self,
        _session: SessionPayload | None,
        query: Mapping[str, Any],
    ) -> list[dict]:
        """查询客户端资源并组装为树结构。"""
        resources = await self.repo.list_resources(
            module_id=query["module_id"],
            account_type=query["account_type"],
        )
        return await self._build_tree_nodes(resources)

    async def bind_permission(
        self,
        payload: Mapping[str, Any],
        _session: SessionPayload | None = None,
    ) -> dict:
        """校验权限码后绑定客户端资源权限。"""
        await ensure_registered_permission_key(payload["permission_key"])
        resource = await self.repo.get_required(payload["resource_id"])
        audit_snapshots.subject(resource["name"])
        audit_snapshots.resource_id(resource["id"])
        async with transactional(self.db):
            relation = await self.repo.bind_permission(payload)
        account_type_val = payload["account_type"]
        data_scope_val = payload["data_scope"]
        if hasattr(account_type_val, "value"):
            account_type_val = account_type_val.value
        if hasattr(data_scope_val, "value"):
            data_scope_val = data_scope_val.value
        audit_snapshots.after(
            self.audit.permission_bind_field(
                payload["permission_key"],
                account_type_val,
                data_scope_val,
            )
        )
        if isinstance(relation, dict):
            return relation
        return {
            "id": relation.id,
            "resource_id": relation.subject_id,
            "permission_key": relation.target_key,
            "data_scope": relation.data_scope,
            "custom_scope_dept_ids": list(relation.custom_scope_dept_ids or []),
            "sort": relation.sort,
            "status": relation.status,
            "description": relation.description,
            "created_at": relation.created_at,
            "created_by": relation.created_by,
            "updated_at": relation.updated_at,
            "updated_by": relation.updated_by,
        }

    async def list_grant_modules(
        self,
        account_type: AccountType | None = None,
    ) -> list[Any]:
        """返回授权页所需的客户端资源模块树。"""
        return await self.repo.list_all_client_resource_grant_modules(account_type=account_type)

    async def _fill_module_meta_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        include_account_type: bool = False,
    ) -> list[dict[str, Any]]:
        meta = await self.repo.list_module_meta_map(
            [item.get("module_id") for item in rows if item.get("module_id")]
        )
        out: list[dict[str, Any]] = []
        for raw in rows:
            item = dict(raw)
            name, account_type = meta.get(item.get("module_id") or "", ("", None))
            item["module_id_name"] = name
            if include_account_type:
                item["account_type"] = AccountType(account_type) if account_type else None
            out.append(item)
        return out

    async def _build_tree_nodes(
        self,
        resources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        meta = await self.repo.list_module_meta_map(
            [r.get("module_id") for r in resources if r.get("module_id")]
        )
        ids = {r["id"] for r in resources}
        node_map: dict[str, dict[str, Any]] = {}
        for resource in resources:
            node = dict(resource)
            name, account_type = meta.get(node.get("module_id") or "", ("", None))
            node["module_id_name"] = name
            node["account_type"] = AccountType(account_type) if account_type else None
            node["weight"] = node.get("sort") or 0
            node.setdefault("children", None)
            node_map[str(resource["id"])] = node
        roots: list[dict[str, Any]] = []
        for resource in resources:
            node = node_map[str(resource["id"])]
            parent_id = resource.get("parent_id")
            if parent_id and str(parent_id) in ids:
                parent_node = node_map[str(parent_id)]
                node["parent_id_name"] = parent_node.get("name")
                children = parent_node.get("children")
                if not isinstance(children, list):
                    children = []
                    parent_node["children"] = children
                children.append(node)
            else:
                roots.append(node)
        return roots
