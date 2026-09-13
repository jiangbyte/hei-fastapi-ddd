""" Author: Charlie

客户端模块/资源应用服务：CRUD、树组装与授权模块渲染。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.support import audit as iam_audit
from hei_fastapi_ddd.contexts.iam.domain.enums import (
    IamRelationSubjectType,
    IamRelationTargetType,
    IamRelationType,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.client_po import (
    SysClientModule,
    SysClientResource,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.client_repository import (
    ClientModuleRepository,
    ClientResourceRepository,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_po import SysIamRelation
from hei_fastapi_ddd.contexts.iam.interfaces.http.client_schemas import (
    ClientModuleAdminPageQuery,
    ClientModuleCreateRequest,
    ClientModuleSelectorQuery,
    ClientModuleUpdateRequest,
    ClientResourceAdminPageQuery,
    ClientResourceCreateRequest,
    ClientResourcePermissionBindRequest,
    ClientResourceTreeNode,
    ClientResourceTreeQuery,
    ClientResourceUpdateRequest,
    SysClientModuleSchema,
    SysClientResourcePermissionRelSchema,
    SysClientResourceSchema,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.iam_schemas import ResourceGrantModuleOption
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, to_schema, to_schema_list
from hei_fastapi_ddd.shared.security.permission_registry import ensure_registered_permission_key
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page


class ClientModuleService:
    """客户端模块应用服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ClientModuleRepository(db)

    async def create(self, payload: ClientModuleCreateRequest) -> None:
        """创建客户端模块。"""
        entity: SysClientModule | None = None
        async with transactional(self.db):
            entity = await self.repo.create(payload)
        if entity is not None:
            audit_snapshots.created_entity(entity)

    async def update(self, payload: ClientModuleUpdateRequest) -> None:
        """更新客户端模块。"""
        existing = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
        updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest) -> None:
        """批量删除客户端模块。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = list(
            (
                await self.db.execute(
                    select(SysClientModule).where(SysClientModule.id.in_(unique_ids))
                )
            )
            .scalars()
            .all()
        )
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(self, query: IdQuery) -> SysClientModuleSchema:
        """查询客户端模块详情并回显创建人/更新人昵称。"""
        schema = to_schema(SysClientModuleSchema, await self.repo.get_required(query.id))
        return schema

    async def page_admin(
        self,
        query: ClientModuleAdminPageQuery,
    ) -> PageData[SysClientModuleSchema]:
        """分页查询客户端模块。"""
        items, total = await self.repo.page_admin(query)
        schemas = to_schema_list(SysClientModuleSchema, items)
        return build_page(query, total, schemas)

    async def selector(
        self,
        query: ClientModuleSelectorQuery,
    ) -> list[SysClientModuleSchema]:
        """返回启用的客户端模块（对齐 hei-boot 全字段 selector）。"""
        items = await self.repo.list_enabled(query.account_type)
        schemas = to_schema_list(SysClientModuleSchema, items)
        return schemas


class ClientResourceService:
    """客户端资源应用服务，负责资源 CRUD、树组装与权限绑定。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ClientResourceRepository(db)

    async def create(self, payload: ClientResourceCreateRequest) -> None:
        """创建客户端资源。"""
        entity: SysClientResource | None = None
        async with transactional(self.db):
            entity = await self.repo.create(payload)
        if entity is not None:
            audit_snapshots.created_entity(entity)

    async def update(self, payload: ClientResourceUpdateRequest) -> None:
        """更新客户端资源。"""
        existing = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
        updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest) -> None:
        """批量删除客户端资源。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = list(
            (
                await self.db.execute(
                    select(SysClientResource).where(SysClientResource.id.in_(unique_ids))
                )
            )
            .scalars()
            .all()
        )
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(self, query: IdQuery) -> SysClientResourceSchema:
        """查询客户端资源详情，填充模块元信息与创建人昵称。"""
        entity = await self.repo.get_required(query.id)
        schema = to_schema(SysClientResourceSchema, entity)
        await self._fill_module_meta([schema], include_account_type=True)
        return schema

    async def page_admin(
        self,
        query: ClientResourceAdminPageQuery,
    ) -> PageData[SysClientResourceSchema]:
        """分页查询客户端资源。"""
        items, total = await self.repo.page_admin(query)
        schemas = to_schema_list(SysClientResourceSchema, items)
        await self._fill_module_meta(schemas)
        return build_page(query, total, schemas)

    async def list_tree(
        self,
        _session: SessionPayload | None,
        query: ClientResourceTreeQuery,
    ) -> list[ClientResourceTreeNode]:
        """查询客户端资源并组装为树结构。"""
        resources = await self.repo.list_resources(
            module_id=query.module_id,
            account_type=query.account_type,
        )
        return await self._build_tree_nodes(resources)

    async def bind_permission(
        self,
        payload: ClientResourcePermissionBindRequest,
        _session: SessionPayload | None = None,
    ) -> SysClientResourcePermissionRelSchema:
        """校验权限码后绑定客户端资源权限。"""
        await ensure_registered_permission_key(payload.permission_key)
        resource = await self.repo.get_required(payload.resource_id)
        audit_snapshots.subject(resource.name)
        audit_snapshots.resource_id(resource.id)
        old_stmt = select(SysIamRelation).where(
            SysIamRelation.subject_type == IamRelationSubjectType.CLIENT_RESOURCE.value,
            SysIamRelation.subject_id == payload.resource_id,
            SysIamRelation.relation_type == IamRelationType.CLIENT_RESOURCE_PERMISSION.value,
            SysIamRelation.target_type == IamRelationTargetType.PERMISSION.value,
            SysIamRelation.account_type == payload.account_type.value,
        )
        old_permissions = list((await self.db.execute(old_stmt)).scalars().all())
        old = next(
            (item for item in old_permissions if item.target_key == payload.permission_key),
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
            relation = await self.repo.bind_permission(payload)
        audit_snapshots.after(
            iam_audit.permission_bind_field(
                payload.permission_key,
                payload.account_type.value,
                payload.data_scope.value,
            )
        )
        return SysClientResourcePermissionRelSchema(
            id=relation.id,
            resource_id=relation.subject_id,
            permission_key=relation.target_key,
            data_scope=relation.data_scope,
            custom_scope_dept_ids=list(relation.custom_scope_dept_ids or []),
            sort=relation.sort,
            status=relation.status,
            description=relation.description,
            created_at=relation.created_at,
            created_by=relation.created_by,
            updated_at=relation.updated_at,
            updated_by=relation.updated_by,
        )

    async def list_grant_modules(
        self,
        account_type: AccountType | None = None,
    ) -> list[ResourceGrantModuleOption]:
        """返回授权页所需的客户端资源模块树。"""
        return await self.repo.list_all_client_resource_grant_modules(account_type=account_type)

    async def _fill_module_meta(
        self,
        schemas: list[SysClientResourceSchema],
        *,
        include_account_type: bool = False,
    ) -> None:
        """批量填充模块名称；account_type 仅详情/树需要（对齐 hei-boot 分页）。"""
        meta = await self.repo.list_module_meta_map(
            [item.module_id for item in schemas if item.module_id]
        )
        for schema in schemas:
            name, account_type = meta.get(schema.module_id or "", ("", None))
            schema.module_id_name = name
            if include_account_type:
                schema.account_type = AccountType(account_type) if account_type else None

    async def _build_tree_nodes(
        self,
        resources: list[SysClientResource],
    ) -> list[ClientResourceTreeNode]:
        """将扁平资源列表组装为带模块元信息的树节点。"""
        meta = await self.repo.list_module_meta_map(
            [resource.module_id for resource in resources if resource.module_id]
        )
        ids = {resource.id for resource in resources}
        node_map = {
            resource.id: to_schema(ClientResourceTreeNode, resource) for resource in resources
        }
        for node in node_map.values():
            name, account_type = meta.get(node.module_id or "", ("", None))
            node.module_id_name = name
            node.account_type = AccountType(account_type) if account_type else None
            node.weight = node.sort or 0
        roots: list[ClientResourceTreeNode] = []
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
