""" Author: Charlie

资源应用服务：资源树/模块 CRUD、权限绑定与授权模块渲染。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.support import audit as iam_audit
from hei_fastapi_ddd.contexts.iam.domain.enums import ResourceType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import (
    IamRelationRepository,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import (
    SysResource,
    SysResourceModule,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_repository import (
    ResourceModuleRepository,
    ResourceRepository,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.iam_schemas import (
    PermissionRegistryItem,
    ResourceGrantModuleOption,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.resource_schemas import (
    ResourceAdminPageQuery,
    ResourceButtonCreateRequest,
    ResourceButtonPageQuery,
    ResourceButtonSchema,
    ResourceButtonUpdateRequest,
    ResourceCreateRequest,
    ResourceModuleAdminPageQuery,
    ResourceModuleCreateRequest,
    ResourceModuleUpdateRequest,
    ResourcePermissionBindRequest,
    ResourceTreeNode,
    ResourceTreeQuery,
    ResourceUpdateRequest,
    SysResourceModuleSchema,
    SysResourcePermissionRelSchema,
    SysResourceSchema,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.exceptions.business import AuthorizationError, ConflictError
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, to_schema, to_schema_list
from hei_fastapi_ddd.shared.security.data_scope import resolve_data_scope_dept_ids
from hei_fastapi_ddd.shared.security.permission_registry import (
    ensure_registered_permission_key,
    list_permission_resources,
)
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page


class ResourceService:
    """资源应用服务，负责资源树/按钮 CRUD、权限绑定与授权渲染。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ResourceRepository(db)

    async def create(self, payload: ResourceCreateRequest) -> None:
        """创建资源。"""
        entity: SysResource | None = None
        async with transactional(self.db):
            entity = await self.repo.create(payload)
        if entity is not None:
            audit_snapshots.created_entity(entity)

    async def update(self, payload: ResourceUpdateRequest) -> None:
        """更新资源。"""
        existing = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
        updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest) -> None:
        """批量删除资源。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = list(
            (
                await self.db.execute(
                    select(SysResource).where(SysResource.id.in_(unique_ids))
                )
            )
            .scalars()
            .all()
        )
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(self, query: IdQuery) -> SysResourceSchema:
        """查询资源详情。"""
        return (await self._build_resource_schemas([await self.repo.get_required(query.id)]))[0]

    async def page_admin(self, query: ResourceAdminPageQuery) -> PageData[SysResourceSchema]:
        """分页查询资源。"""
        items, total = await self.repo.page_admin(query)
        return build_page(query, total, await self._build_resource_schemas(items))

    async def page_buttons(self, query: ResourceButtonPageQuery) -> PageData[ResourceButtonSchema]:
        """分页查询按钮资源。"""
        await self._get_button_parent(query.parent_id)
        items, total = await self.repo.page_buttons(query)
        return build_page(query, total, await self._build_button_schemas(items))

    async def bind_resource_permission(
        self,
        payload: ResourcePermissionBindRequest,
        session: SessionPayload | None = None,
    ) -> SysResourcePermissionRelSchema:
        """校验权限码后绑定资源权限，传入 session 时校验作用域部门可见性。"""
        if session is not None:
            await self._ensure_depts_visible(
                session,
                "iam:resource:grant",
                payload.custom_scope_dept_ids,
            )
        await ensure_registered_permission_key(payload.permission_key)
        resource = await self.repo.get_required(payload.resource_id)
        audit_snapshots.subject(resource.name)
        audit_snapshots.resource_id(resource.id)
        permission_map = await self.repo.list_permissions_by_resource_ids([payload.resource_id])
        old_permissions = permission_map.get(payload.resource_id, [])
        old = next(
            (
                item
                for item in old_permissions
                if item.target_key == payload.permission_key
                and item.account_type == payload.account_type.value
            ),
            None,
        )
        audit_snapshots.before(
            iam_audit.permission_bind_field(
                old.target_key if old else None,
                old.account_type if old else None,
                old.data_scope if old else None,
            )
        )
        async with transactional(self.db):
            relation = await self.repo.bind_resource_permission(payload)
        audit_snapshots.after(
            iam_audit.permission_bind_field(
                payload.permission_key,
                payload.account_type.value,
                payload.data_scope.value,
            )
        )
        return to_schema(
            SysResourcePermissionRelSchema,
            relation,
        )

    async def create_button(
        self,
        payload: ResourceButtonCreateRequest,
        session: SessionPayload | None = None,
    ) -> ResourceButtonSchema:
        """创建按钮资源并绑定权限。"""
        parent = await self._prepare_button_permission(payload, session)
        button: SysResource | None = None
        async with transactional(self.db):
            button = await self.repo.create(self._build_button_resource_payload(payload, parent))
            await self.repo.replace_resource_permission(
                self._build_button_permission_payload(button.id, payload)
            )
        if button is not None:
            audit_snapshots.created_entity(button)
        return (await self._build_button_schemas([button]))[0]

    async def update_button(
        self,
        payload: ResourceButtonUpdateRequest,
        session: SessionPayload | None = None,
    ) -> ResourceButtonSchema:
        """更新按钮资源并重建权限绑定。"""
        button = await self.repo.get_required(payload.id)
        if button.resource_type != ResourceType.BUTTON.value:
            raise ConflictError("Resource is not a button")
        parent = await self._prepare_button_permission(payload, session)
        audit_snapshots.before_entity(button)
        async with transactional(self.db):
            await self.repo.update(
                ResourceUpdateRequest(
                    id=payload.id,
                    **self._build_button_resource_payload(payload, parent).model_dump(),
                )
            )
            await self.repo.replace_resource_permission(
                self._build_button_permission_payload(payload.id, payload)
            )
        updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)
        return (await self._build_button_schemas([updated]))[0]

    async def delete_button(self, payload: IdsRequest) -> None:
        """批量删除按钮资源（单次批量 DELETE，避免逐条 N+1）。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = list(
            (
                await self.db.execute(
                    select(SysResource).where(SysResource.id.in_(unique_ids))
                )
            )
            .scalars()
            .all()
        )
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_buttons(payload.ids)

    async def list_resource_tree(
        self,
        session: SessionPayload,
        query: ResourceTreeQuery,
    ) -> list[ResourceTreeNode]:
        """返回可见资源树（排除按钮/操作节点）。"""
        resources = await self._list_visible_resources(
            session,
            module_id=query.module_id,
            module_client=query.module_client,
        )
        resources = [
            resource
            for resource in resources
            if resource.resource_type not in {ResourceType.BUTTON.value, ResourceType.ACTION.value}
        ]
        return await self._build_resource_tree_nodes(resources)

    async def list_current_resources(
        self,
        session: SessionPayload,
        module_client: AccountType | None = None,
    ) -> list[SysResourceSchema]:
        """返回当前会话可见的资源列表。"""
        resources = await self._list_visible_resources(
            session,
            module_client=module_client,
        )
        return await self._build_resource_schemas(resources)

    async def list_public_portal_resources(self) -> list[SysResourceSchema]:
        """返回门户端公开可见的资源列表。"""
        resources = await self.repo.list_resources(module_client=AccountType.PORTAL)
        return await self._build_resource_schemas(resources)

    async def _list_visible_resources(
        self,
        session: SessionPayload,
        module_id: str | None = None,
        module_client: AccountType | None = None,
    ) -> list[SysResource]:
        """按会话权限计算可见资源，超级权限返回全部。"""
        if "*:*:*" in session.permission_keys:
            return await self.repo.list_resources(
                module_id=module_id,
                module_client=module_client,
            )
        resource_ids = session.resource_ids
        if not resource_ids:
            resource_ids = await IamRelationRepository(self.db).get_account_resource_ids(
                session.account_id
            )
        resources = await self.repo.list_resources_by_ids_with_parents(
            resource_ids,
            module_client=module_client,
        )
        if module_id:
            resources = [resource for resource in resources if resource.module_id == module_id]
        return resources

    async def list_grant_modules(
        self,
        module_client: AccountType | None = None,
    ) -> list[ResourceGrantModuleOption]:
        """返回授权页所需的资源模块树。"""
        return await self.repo.list_all_resource_grant_modules(module_client=module_client)

    async def _build_resource_schemas(
        self,
        resources: list[SysResource],
    ) -> list[SysResourceSchema]:
        """组装资源响应并批量填充模块元信息与创建人昵称。"""
        module_meta_map = await self.repo.list_module_meta_map(
            [resource.module_id for resource in resources if resource.module_id]
        )
        schemas = to_schema_list(SysResourceSchema, resources)
        parent_ids = {schema.parent_id for schema in schemas if schema.parent_id}
        parent_name_map: dict[str, str] = {}
        if parent_ids:
            stmt = select(SysResource.id, SysResource.name).where(SysResource.id.in_(parent_ids))
            rows = (await self.db.execute(stmt)).all()
            parent_name_map = {row[0]: row[1] for row in rows}
        for schema in schemas:
            module_name, module_client = module_meta_map.get(schema.module_id or "", ("", None))
            schema.module_id_name = module_name
            schema.module_client = module_client
            if schema.parent_id:
                schema.parent_id_name = parent_name_map.get(schema.parent_id)
        return schemas

    async def _build_button_schemas(
        self,
        resources: list[SysResource],
    ) -> list[ResourceButtonSchema]:
        """组装按钮响应并挂接首条权限关系信息。"""
        schemas = to_schema_list(ResourceButtonSchema, resources)
        permission_map = await self.repo.list_permissions_by_resource_ids(
            [resource.id for resource in resources]
        )
        for schema in schemas:
            permissions = permission_map.get(schema.id, [])
            permission = permissions[0] if permissions else None
            if permission is None:
                continue
            schema.permission_rel_id = permission.id
            schema.permission_key = permission.permission_key
            schema.data_scope = permission.data_scope
            schema.custom_scope_dept_ids = list(permission.custom_scope_dept_ids or [])
            schema.permission_description = permission.description
        return schemas

    async def _build_resource_tree_nodes(
        self,
        resources: list[SysResource],
    ) -> list[ResourceTreeNode]:
        """组装资源树节点。"""
        module_meta_map = await self.repo.list_module_meta_map(
            [resource.module_id for resource in resources if resource.module_id]
        )
        return _build_resource_tree_nodes(resources, module_meta_map)

    async def list_permission_registry_items(self) -> list[PermissionRegistryItem]:
        """解析 Redis 权限注册表文本为条目结构，按权限码排序。"""
        resources = await list_permission_resources()
        items: list[PermissionRegistryItem] = []
        for resource in resources:
            index = resource.find("[")
            permission_key = resource[:index] if index > -1 else resource
            name = (
                resource[index + 1 : -1]
                if index > -1 and resource.endswith("]")
                else permission_key
            )
            parts = permission_key.split(":")
            items.append(
                PermissionRegistryItem(
                    permission_key=permission_key,
                    name=name,
                    module_code=parts[0] if len(parts) > 0 else None,
                    resource_code=parts[1] if len(parts) > 1 else None,
                    action=parts[2] if len(parts) > 2 else None,
                )
            )
        return sorted(items, key=lambda item: item.permission_key)

    async def _ensure_depts_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        dept_ids: list[str],
    ) -> None:
        """校验目标部门均在当前可见部门集合内，否则抛授权错误。"""
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return
        visible_dept_ids = await resolve_data_scope_dept_ids(self.db, session, permission_key)
        if visible_dept_ids is None:
            return
        allowed_ids = set(visible_dept_ids)
        if any(dept_id not in allowed_ids for dept_id in unique_ids):
            raise AuthorizationError("Dept is outside current data scope")

    async def _get_button_parent(self, parent_id: str) -> SysResource:
        """查询按钮父级并校验其类型（按钮/操作不可作父级）。"""
        parent = await self.repo.get_required(parent_id)
        if parent.resource_type in {ResourceType.BUTTON.value, ResourceType.ACTION.value}:
            raise ConflictError("Button resource cannot be parent resource")
        return parent

    async def _prepare_button_permission(
        self,
        payload: ResourceButtonCreateRequest | ResourceButtonUpdateRequest,
        session: SessionPayload | None,
    ) -> SysResource:
        """校验按钮父级、作用域部门可见性与权限码注册情况。"""
        parent = await self._get_button_parent(payload.parent_id)
        if session is not None:
            await self._ensure_depts_visible(
                session,
                "iam:resource:grant",
                payload.custom_scope_dept_ids,
            )
        await ensure_registered_permission_key(payload.permission_key)
        return parent

    def _build_button_resource_payload(
        self,
        payload: ResourceButtonCreateRequest | ResourceButtonUpdateRequest,
        parent: SysResource,
    ) -> ResourceCreateRequest:
        """由按钮请求构造底层资源创建载荷（继承父级模块归属）。"""
        return ResourceCreateRequest(
            code=payload.code,
            name=payload.name,
            resource_type=ResourceType.BUTTON,
            parent_id=parent.id,
            module_id=parent.module_id,
            path=None,
            component=None,
            redirect=None,
            icon=None,
            color=None,
            href=None,
            sort=payload.sort,
            is_visible=False,
            is_cache=False,
            is_affix=False,
            status=payload.status,
            description=payload.description,
            extra={},
        )

    def _build_button_permission_payload(
        self,
        button_id: str,
        payload: ResourceButtonCreateRequest | ResourceButtonUpdateRequest,
    ) -> ResourcePermissionBindRequest:
        """由按钮请求构造权限绑定载荷。"""
        return ResourcePermissionBindRequest(
            resource_id=button_id,
            permission_key=payload.permission_key,
            data_scope=payload.data_scope,
            custom_scope_dept_ids=payload.custom_scope_dept_ids,
            sort=payload.sort,
            description=payload.description,
        )


class ResourceModuleService:
    """资源模块应用服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ResourceModuleRepository(db)

    async def create(self, payload: ResourceModuleCreateRequest) -> None:
        """创建资源模块。"""
        async with transactional(self.db):
            await self.repo.create(payload)
        entity = (
            await self.db.execute(
                select(SysResourceModule).where(SysResourceModule.code == payload.code).limit(1)
            )
        ).scalar_one()
        audit_snapshots.created_entity(entity)

    async def update(self, payload: ResourceModuleUpdateRequest) -> None:
        """更新资源模块。"""
        existing = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
        updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest) -> None:
        """批量删除资源模块。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = list(
            (
                await self.db.execute(
                    select(SysResourceModule).where(SysResourceModule.id.in_(unique_ids))
                )
            )
            .scalars()
            .all()
        )
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(self, query: IdQuery) -> SysResourceModuleSchema:
        """查询资源模块详情并回显创建人昵称。"""
        schema = to_schema(SysResourceModuleSchema, await self.repo.get_required(query.id))
        return schema

    async def page_admin(
        self,
        query: ResourceModuleAdminPageQuery,
    ) -> PageData[SysResourceModuleSchema]:
        """分页查询资源模块。"""
        items, total = await self.repo.page_admin(query)
        schemas = to_schema_list(SysResourceModuleSchema, items)
        return build_page(query, total, schemas)

    async def selector(self) -> list[SysResourceModuleSchema]:
        """返回启用的资源模块（对齐 hei-boot 全字段 selector）。"""
        items = await self.repo.list_enabled_modules(None)
        schemas = to_schema_list(SysResourceModuleSchema, items)
        return schemas


def _build_resource_tree_nodes(
    resources: list[SysResource],
    module_meta_map: dict[str, tuple[str, str]],
) -> list[ResourceTreeNode]:
    """将扁平资源列表组装为带模块元信息的树节点（对齐 hei-boot TreeUtil）。"""
    ids = {resource.id for resource in resources}
    node_map = {resource.id: to_schema(ResourceTreeNode, resource) for resource in resources}
    for node in node_map.values():
        module_name, module_client = module_meta_map.get(node.module_id or "", ("", None))
        node.module_id_name = module_name
        node.module_client = module_client
        node.weight = node.sort or 0
    roots: list[ResourceTreeNode] = []
    for resource in resources:
        node = node_map[resource.id]
        parent_id = resource.parent_id
        if parent_id and parent_id in ids:
            parent_node = node_map[parent_id]
            node.parent_id_name = parent_node.name
            if parent_node.children is None:
                parent_node.children = []
            parent_node.children.append(node)
        else:
            roots.append(node)
    return roots
