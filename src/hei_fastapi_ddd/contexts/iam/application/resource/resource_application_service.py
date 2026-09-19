"""Author: Charlie

资源应用服务：依赖 domain 仓储端口，不依赖 infrastructure / api。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.support.audit_port import IamAuditPort
from hei_fastapi_ddd.contexts.iam.domain.enums import ResourceType
from hei_fastapi_ddd.contexts.iam.domain.relation.repository import IamRelationRepositoryPort
from hei_fastapi_ddd.contexts.iam.domain.resource.repository import (
    ResourceModuleRepository,
    ResourceRepository,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.data_scope import resolve_data_scope_dept_ids
from hei_fastapi_ddd.shared.security.permission_registry import (
    ensure_registered_permission_key,
    list_permission_resources,
)
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import AuthorizationError, ConflictError

class ResourceService:
    """资源应用服务，负责资源树/按钮 CRUD、权限绑定与授权渲染。"""

    def __init__(
        self,
        db: AsyncSession,
        audit: IamAuditPort,
        *,
        repo: ResourceRepository,
        relation_repo: IamRelationRepositoryPort,
    ):
        self.db = db
        self.audit = audit
        self.repo = repo
        self.relation_repo = relation_repo

    async def create(self, payload: Mapping[str, Any]) -> None:
        """创建资源。"""
        entity: dict[str, Any] | None = None
        async with transactional(self.db):
            entity = await self.repo.create(payload)
        if entity is not None:
            audit_snapshots.created_entity(entity)

    async def update(self, payload: Mapping[str, Any]) -> None:
        """更新资源。"""
        existing = await self.repo.get_required(payload["id"])
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
        updated = await self.repo.get_required(payload["id"])
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest) -> None:
        """批量删除资源。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = await self.repo.list_by_ids(unique_ids)
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(self, query: IdQuery) -> dict:
        """查询资源详情。"""
        return (await self._build_resource_schemas([await self.repo.get_required(query.id)]))[0]

    async def page_admin(self, query: Mapping[str, Any]) -> PageData[dict]:
        """分页查询资源。"""
        items, total = await self.repo.page_admin(query)
        return build_page(query, total, await self._build_resource_schemas(items))

    async def page_buttons(self, query: Mapping[str, Any]) -> PageData[dict]:
        """分页查询按钮资源。"""
        await self._get_button_parent(query["parent_id"])
        items, total = await self.repo.page_buttons(query)
        return build_page(query, total, await self._build_button_schemas(items))

    async def bind_resource_permission(
        self,
        payload: Mapping[str, Any],
        session: SessionPayload | None = None,
    ) -> dict:
        """校验权限码后绑定资源权限，传入 session 时校验作用域部门可见性。"""
        if session is not None:
            await self._ensure_depts_visible(
                session,
                "iam:resource:grant",
                payload["custom_scope_dept_ids"],
            )
        await ensure_registered_permission_key(payload["permission_key"])
        resource = await self.repo.get_required(payload["resource_id"])
        audit_snapshots.subject(resource["name"])
        audit_snapshots.resource_id(resource["id"])
        permission_map = await self.repo.list_permissions_by_resource_ids([payload["resource_id"]])
        old_permissions = permission_map.get(payload["resource_id"], [])
        def _perm_key(item: Any) -> str | None:
            if isinstance(item, dict):
                return item.get("target_key") or item.get("permission_key")
            return getattr(item, "target_key", None)

        def _perm_account(item: Any) -> Any:
            if isinstance(item, dict):
                return item.get("account_type")
            return getattr(item, "account_type", None)

        def _perm_scope(item: Any) -> Any:
            if isinstance(item, dict):
                return item.get("data_scope")
            return getattr(item, "data_scope", None)

        account_type_val = payload["account_type"]
        if hasattr(account_type_val, "value"):
            account_type_val = account_type_val.value
        old = next(
            (
                item
                for item in old_permissions
                if _perm_key(item) == payload["permission_key"]
                and _perm_account(item) == account_type_val
            ),
            None,
        )
        audit_snapshots.before(
            self.audit.permission_bind_field(
                _perm_key(old),
                _perm_account(old),
                _perm_scope(old),
            )
        )
        async with transactional(self.db):
            relation = await self.repo.bind_resource_permission(payload)
        audit_snapshots.after(
            self.audit.permission_bind_field(
                payload["permission_key"],
                payload["account_type"].value,
                payload["data_scope"].value,
            )
        )
        if isinstance(relation, dict):
            return relation
        return dict(relation.__dict__) if hasattr(relation, "__dict__") else {"id": getattr(relation, "id", None)}

    async def create_button(
        self,
        payload: Mapping[str, Any],
        session: SessionPayload | None = None,
    ) -> dict:
        """创建按钮资源并绑定权限。"""
        parent = await self._prepare_button_permission(payload, session)
        button: dict[str, Any] | None = None
        async with transactional(self.db):
            button = await self.repo.create(self._build_button_resource_payload(payload, parent))
            await self.repo.replace_resource_permission(
                self._build_button_permission_payload(button["id"], payload)
            )
        if button is not None:
            audit_snapshots.created_entity(button)
        return (await self._build_button_schemas([button]))[0]

    async def update_button(
        self,
        payload: Mapping[str, Any],
        session: SessionPayload | None = None,
    ) -> dict:
        """更新按钮资源并重建权限绑定。"""
        button = await self.repo.get_required(payload["id"])
        if button["resource_type"] != ResourceType.BUTTON.value:
            raise ConflictError("Resource is not a button")
        parent = await self._prepare_button_permission(payload, session)
        audit_snapshots.before_entity(button)
        async with transactional(self.db):
            update_data = dict(self._build_button_resource_payload(payload, parent))
            update_data["id"] = payload["id"]
            await self.repo.update(update_data)
            await self.repo.replace_resource_permission(
                self._build_button_permission_payload(payload["id"], payload)
            )
        updated = await self.repo.get_required(payload["id"])
        audit_snapshots.after_entity(updated)
        return (await self._build_button_schemas([updated]))[0]

    async def delete_button(self, payload: IdsRequest) -> None:
        """批量删除按钮资源（单次批量 DELETE，避免逐条 N+1）。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = await self.repo.list_by_ids(unique_ids)
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_buttons(payload.ids)

    async def list_resource_tree(
        self,
        session: SessionPayload,
        query: Mapping[str, Any],
    ) -> list[dict]:
        """返回可见资源树（排除按钮/操作节点）。"""
        resources = await self._list_visible_resources(
            session,
            module_id=query["module_id"],
            module_client=query["module_client"],
        )
        resources = [
            resource
            for resource in resources
            if resource["resource_type"] not in {ResourceType.BUTTON.value, ResourceType.ACTION.value}
        ]
        return await self._build_resource_tree_nodes(resources)

    async def list_current_resources(
        self,
        session: SessionPayload,
        module_client: AccountType | None = None,
    ) -> list[dict]:
        """返回当前会话可见的资源列表。"""
        resources = await self._list_visible_resources(
            session,
            module_client=module_client,
        )
        return await self._build_resource_schemas(resources)

    async def list_public_portal_resources(self) -> list[dict]:
        """返回门户端公开可见的资源列表。"""
        resources = await self.repo.list_resources(module_client=AccountType.PORTAL)
        return await self._build_resource_schemas(resources)

    async def _list_visible_resources(
        self,
        session: SessionPayload,
        module_id: str | None = None,
        module_client: AccountType | None = None,
    ) -> list[dict[str, Any]]:
        """按会话权限计算可见资源，超级权限返回全部。"""
        if "*:*:*" in session.permission_keys:
            return await self.repo.list_resources(
                module_id=module_id,
                module_client=module_client,
            )
        resource_ids = session.resource_ids
        if not resource_ids:
            resource_ids = await self.relation_repo.get_account_resource_ids(
                session.account_id
            )
        resources = await self.repo.list_resources_by_ids_with_parents(
            resource_ids,
            module_client=module_client,
        )
        if module_id:
            resources = [resource for resource in resources if resource["module_id"] == module_id]
        return resources

    async def list_grant_modules(
        self,
        module_client: AccountType | None = None,
    ) -> list[Any]:
        """返回授权页所需的资源模块树。"""
        return await self.repo.list_all_resource_grant_modules(module_client=module_client)

    async def _build_resource_schemas(
        self,
        resources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """组装资源行并填充模块与父级名称。"""
        if not resources:
            return []
        module_meta_map = await self.repo.list_module_meta_map(
            [r["module_id"] for r in resources if r.get("module_id")]
        )
        parent_ids = {r["parent_id"] for r in resources if r.get("parent_id")}
        parent_name_map = (
            await self.repo.list_parent_names(list(parent_ids)) if parent_ids else {}
        )
        rows: list[dict[str, Any]] = []
        for raw in resources:
            item = dict(raw)
            mid = item.get("module_id") or ""
            module_name, module_client = module_meta_map.get(mid, ("", None))
            item["module_id_name"] = module_name
            item["module_client"] = module_client
            pid = item.get("parent_id")
            if pid:
                item["parent_id_name"] = parent_name_map.get(str(pid))
            rows.append(item)
        return rows

    async def _build_button_schemas(
        self,
        resources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """组装按钮行并挂接首条权限关系。"""
        if not resources:
            return []
        permission_map = await self.repo.list_permissions_by_resource_ids(
            [r["id"] for r in resources]
        )
        rows: list[dict[str, Any]] = []
        for raw in resources:
            item = dict(raw)
            permissions = permission_map.get(str(item["id"]), [])
            permission = permissions[0] if permissions else None
            if permission is not None:
                if isinstance(permission, dict):
                    item["permission_rel_id"] = permission.get("id")
                    item["permission_key"] = permission.get("permission_key") or permission.get("target_key")
                    item["data_scope"] = permission.get("data_scope")
                    item["custom_scope_dept_ids"] = list(permission.get("custom_scope_dept_ids") or [])
                    item["permission_description"] = permission.get("description")
                else:
                    item["permission_rel_id"] = getattr(permission, "id", None)
                    item["permission_key"] = getattr(permission, "target_key", None)
                    item["data_scope"] = getattr(permission, "data_scope", None)
                    item["custom_scope_dept_ids"] = list(getattr(permission, "custom_scope_dept_ids", None) or [])
                    item["permission_description"] = getattr(permission, "description", None)
            rows.append(item)
        return rows

    async def _build_resource_tree_nodes(
        self,
        resources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        module_meta_map = await self.repo.list_module_meta_map(
            [r["module_id"] for r in resources if r.get("module_id")]
        )
        return _build_resource_tree_nodes(resources, module_meta_map)


class ResourceModuleService:
    """资源模块应用服务。"""

    def __init__(self, db: AsyncSession, repo: ResourceModuleRepository):
        self.db = db
        self.repo = repo

    async def create(self, payload: Mapping[str, Any]) -> None:
        async with transactional(self.db):
            entity = await self.repo.create(payload)
        audit_snapshots.created_entity(entity)

    async def update(self, payload: Mapping[str, Any]) -> None:
        existing = await self.repo.get_required(str(payload["id"]))
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
        updated = await self.repo.get_required(str(payload["id"]))
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest) -> None:
        entities = await self.repo.list_by_ids(list(dict.fromkeys(payload.ids)))
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(self, query: IdQuery) -> dict[str, Any]:
        return await self.repo.get_required(query.id)

    async def page_admin(self, query: Mapping[str, Any]) -> PageData[dict]:
        items, total = await self.repo.page_admin(query)
        return build_page(query, total, items)

    async def selector(self) -> list[dict[str, Any]]:
        return await self.repo.list_enabled_modules(None)


def _build_resource_tree_nodes(
    resources: list[dict[str, Any]],
    module_meta_map: dict[str, tuple[str, str | None]],
) -> list[dict[str, Any]]:
    ids = {r["id"] for r in resources}
    node_map: dict[str, dict[str, Any]] = {}
    for resource in resources:
        node = dict(resource)
        module_name, module_client = module_meta_map.get(node.get("module_id") or "", ("", None))
        node["module_id_name"] = module_name
        node["module_client"] = module_client
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
