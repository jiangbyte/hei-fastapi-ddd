""" Author: Charlie

客户端模块/资源仓储：负责客户端模块与客户端资源树的增删改查及权限挂载。
"""

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum
from hei_fastapi_ddd.shared.exceptions.business import ConflictError, NotFoundError
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.client_po import SysClientModule, SysClientResource
from hei_fastapi_ddd.contexts.iam.interfaces.http.client_schemas import (
    ClientModuleAdminPageQuery,
    ClientModuleCreateRequest,
    ClientModuleUpdateRequest,
    ClientResourceAdminPageQuery,
    ClientResourceCreateRequest,
    ClientResourcePermissionBindRequest,
    ClientResourceUpdateRequest,
)
from hei_fastapi_ddd.contexts.iam.domain.enums import (
    IamRelationSubjectType,
    IamRelationTargetType,
    IamRelationType,
    ResourceType,
)
from hei_fastapi_ddd.contexts.iam.application.reference_guard import (
    ensure_not_self_or_descendant,
    list_descendant_ids_many,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_po import SysIamRelation
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import IamRelationRepository
from hei_fastapi_ddd.contexts.iam.interfaces.http.iam_schemas import (
    ResourceGrantMenuOption,
    ResourceGrantModuleOption,
    ResourcePermissionOption,
)


class ClientModuleRepository:
    """客户端模块仓储。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: ClientModuleCreateRequest) -> SysClientModule:
        """创建客户端模块，编码已存在时抛冲突错误。"""
        await self._ensure_code_unique(payload.code)
        entity = SysClientModule(**payload.model_dump())
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id(self, module_id: str) -> SysClientModule | None:
        """按主键查询客户端模块。"""
        return await self.db.get(SysClientModule, module_id)

    async def get_required(self, module_id: str) -> SysClientModule:
        """按主键查询客户端模块，不存在时抛 NotFoundError。"""
        entity = await self.get_by_id(module_id)
        if entity is None:
            raise NotFoundError("Client module not found")
        return entity

    async def update(self, payload: ClientModuleUpdateRequest) -> None:
        """更新客户端模块，编码被其他模块占用时抛冲突错误。"""
        entity = await self.get_required(payload.id)
        await self._ensure_code_unique(payload.code, payload.id)
        for key, value in payload.model_dump(exclude={"id"}).items():
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, module_ids: list[str]) -> None:
        """删除客户端模块，存在下属资源时拒绝删除。"""
        unique_ids = list(dict.fromkeys(module_ids))
        if not unique_ids:
            return
        existing = set(
            (
                await self.db.execute(
                    select(SysClientModule.id).where(SysClientModule.id.in_(unique_ids))
                )
            )
            .scalars()
            .all()
        )
        if len(existing) != len(unique_ids):
            raise NotFoundError("Client module not found")
        resource_count = int(
            (
                await self.db.execute(
                    select(func.count(SysClientResource.id)).where(
                        SysClientResource.module_id.in_(unique_ids)
                    )
                )
            ).scalar_one()
        )
        if resource_count > 0:
            raise ConflictError(f"Client module is referenced: resources={resource_count}")
        await self.db.execute(delete(SysClientModule).where(SysClientModule.id.in_(unique_ids)))

    async def page_admin(
        self,
        query: ClientModuleAdminPageQuery,
    ) -> tuple[list[SysClientModule], int]:
        """按条件分页查询客户端模块并统计总数。"""
        stmt: Select[tuple[SysClientModule]] = select(SysClientModule)
        count_stmt = select(func.count(SysClientModule.id))
        filters = []
        if query.name:
            filters.append(SysClientModule.name.contains(query.name))
        if query.code:
            filters.append(SysClientModule.code.contains(query.code))
        if query.status:
            filters.append(SysClientModule.status == query.status)
        if query.account_type:
            filters.append(SysClientModule.account_type == query.account_type.value)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysClientModule.sort.asc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def list_enabled(
        self,
        account_type: AccountType | None = None,
    ) -> list[SysClientModule]:
        """列出启用的客户端模块，可按账户体系过滤。"""
        stmt = (
            select(SysClientModule)
            .where(SysClientModule.status == StatusEnum.ENABLED.value)
            .order_by(SysClientModule.sort.asc())
        )
        if account_type:
            stmt = stmt.where(SysClientModule.account_type == account_type.value)
        return list((await self.db.execute(stmt)).scalars().all())

    async def _ensure_code_unique(self, code: str, module_id: str | None = None) -> None:
        """校验模块编码唯一，重复时抛冲突错误。"""
        stmt = select(SysClientModule.id).where(SysClientModule.code == code)
        if module_id is not None:
            stmt = stmt.where(SysClientModule.id != module_id)
        if (await self.db.execute(stmt)).scalar_one_or_none() is not None:
            raise ConflictError("Client module code already exists")


class ClientResourceRepository:
    """客户端资源树仓储，负责资源节点 CRUD 与权限挂载。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.relations = IamRelationRepository(db)

    async def create(self, payload: ClientResourceCreateRequest) -> SysClientResource:
        """创建客户端资源节点，先校验模块、父级与编码合法性。"""
        await self._ensure_payload_valid(payload)
        entity = SysClientResource(**payload.model_dump())
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id(self, resource_id: str) -> SysClientResource | None:
        """按主键查询客户端资源。"""
        return await self.db.get(SysClientResource, resource_id)

    async def get_required(self, resource_id: str) -> SysClientResource:
        """按主键查询客户端资源，不存在时抛 NotFoundError。"""
        entity = await self.get_by_id(resource_id)
        if entity is None:
            raise NotFoundError("Client resource not found")
        return entity

    async def update(self, payload: ClientResourceUpdateRequest) -> None:
        """更新客户端资源，校验层级与编码合法性。"""
        entity = await self.get_required(payload.id)
        await ensure_not_self_or_descendant(
            self.db,
            SysClientResource,
            payload.id,
            payload.parent_id,
            "Client resource",
        )
        await self._ensure_payload_valid(payload, payload.id)
        for key, value in payload.model_dump(exclude={"id"}).items():
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, resource_ids: list[str]) -> None:
        """删除客户端资源，存在子节点时拒绝删除。"""
        unique_ids = list(dict.fromkeys(resource_ids))
        if not unique_ids:
            return
        existing = set(
            (
                await self.db.execute(
                    select(SysClientResource.id).where(SysClientResource.id.in_(unique_ids))
                )
            )
            .scalars()
            .all()
        )
        if len(existing) != len(unique_ids):
            raise NotFoundError("Client resource not found")
        descendants_map = await list_descendant_ids_many(self.db, SysClientResource, unique_ids)
        if any(descendants_map.values()):
            raise ConflictError("Client resource has children")
        await self.db.execute(
            delete(SysClientResource).where(SysClientResource.id.in_(unique_ids))
        )

    async def page_admin(
        self,
        query: ClientResourceAdminPageQuery,
    ) -> tuple[list[SysClientResource], int]:
        """按条件分页查询客户端资源并统计总数。"""
        stmt: Select[tuple[SysClientResource]] = select(SysClientResource)
        count_stmt = select(func.count(SysClientResource.id))
        filters = []
        if query.code:
            filters.append(SysClientResource.code.contains(query.code))
        if query.name:
            filters.append(SysClientResource.name.contains(query.name))
        if query.resource_type:
            filters.append(SysClientResource.resource_type == query.resource_type.value)
        if query.module_id:
            filters.append(SysClientResource.module_id == query.module_id)
        if query.parent_id:
            filters.append(SysClientResource.parent_id == query.parent_id)
        if query.status:
            filters.append(SysClientResource.status == query.status)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysClientResource.sort.asc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def list_resources(
        self,
        module_id: str | None = None,
        account_type: AccountType | None = None,
    ) -> list[SysClientResource]:
        """列出启用的客户端资源，可按模块或账户体系过滤。"""
        stmt = (
            select(SysClientResource)
            .where(SysClientResource.status == StatusEnum.ENABLED.value)
            .order_by(SysClientResource.sort.asc(), SysClientResource.id.asc())
        )
        if module_id:
            stmt = stmt.where(SysClientResource.module_id == module_id)
        if account_type:
            stmt = stmt.join(
                SysClientModule, SysClientModule.id == SysClientResource.module_id
            ).where(SysClientModule.account_type == account_type.value)
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_module_meta_map(
        self,
        module_ids: list[str],
    ) -> dict[str, tuple[str, str]]:
        """module_id -> (module_name, account_type)."""
        unique_ids = list(dict.fromkeys(module_ids))
        if not unique_ids:
            return {}
        rows = (
            await self.db.execute(
                select(
                    SysClientModule.id,
                    SysClientModule.name,
                    SysClientModule.account_type,
                ).where(SysClientModule.id.in_(unique_ids))
            )
        ).all()
        return {
            str(module_id): (str(name), str(account_type))
            for module_id, name, account_type in rows
        }

    async def bind_permission(
        self,
        payload: ClientResourcePermissionBindRequest,
    ) -> SysIamRelation:
        """替换客户端资源的权限挂载并返回新关系。"""
        if not await self.db.get(SysClientResource, payload.resource_id):
            raise NotFoundError("Client resource not found")
        await self.relations.delete_subject_relations(
            IamRelationSubjectType.CLIENT_RESOURCE.value,
            payload.resource_id,
            IamRelationType.CLIENT_RESOURCE_PERMISSION,
            account_type=payload.account_type.value,
            target_key=payload.permission_key,
        )
        relation = self.relations.client_resource_permission(
            payload.resource_id,
            payload.permission_key,
            payload.account_type,
            data_scope=payload.data_scope,
            custom_scope_dept_ids=payload.custom_scope_dept_ids,
            sort=payload.sort,
            description=payload.description,
        )
        self.db.add(relation)
        await self.db.flush()
        return relation

    async def list_client_resource_permissions(
        self,
        account_type: AccountType | None = None,
    ) -> list[SysIamRelation]:
        """列出启用中的客户端资源权限关系，可按账户体系过滤。"""
        stmt = (
            select(SysIamRelation)
            .where(
                SysIamRelation.subject_type == IamRelationSubjectType.CLIENT_RESOURCE.value,
                SysIamRelation.relation_type == IamRelationType.CLIENT_RESOURCE_PERMISSION.value,
                SysIamRelation.target_type == IamRelationTargetType.PERMISSION.value,
                SysIamRelation.status == StatusEnum.ENABLED.value,
            )
            .order_by(SysIamRelation.sort.asc(), SysIamRelation.id.asc())
        )
        if account_type is not None:
            stmt = stmt.where(SysIamRelation.account_type == account_type.value)
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_all_client_resource_grant_modules(
        self,
        account_type: AccountType | None = None,
    ) -> list[ResourceGrantModuleOption]:
        """组装授权页所需的客户端资源模块树（模块-菜单-按钮/权限）。"""
        resources = await self.list_resources(account_type=account_type)
        permissions = await self.list_client_resource_permissions(account_type=account_type)
        modules = await ClientModuleRepository(self.db).list_enabled(account_type=account_type)
        permission_map: dict[str, list[ResourcePermissionOption]] = {}
        for permission in permissions:
            permission_map.setdefault(permission.subject_id, []).append(
                ResourcePermissionOption(
                    id=permission.id,
                    permission_key=permission.target_key,
                    title=permission.description or permission.target_key,
                    data_scope=permission.data_scope,
                )
            )
        resource_map = {resource.id: resource for resource in resources}
        child_permission_map: dict[str, list[ResourcePermissionOption]] = {}
        for resource in resources:
            if resource.resource_type not in {ResourceType.BUTTON.value, ResourceType.ACTION.value}:
                continue
            if not resource.parent_id:
                continue
            options = permission_map.get(resource.id)
            if not options:
                options = [
                    ResourcePermissionOption(
                        id=resource.id,
                        permission_key=resource.code,
                        title=resource.name,
                    )
                ]
            child_permission_map.setdefault(resource.parent_id, []).extend(options)
        module_map: dict[str, ResourceGrantModuleOption] = {
            module.id: ResourceGrantModuleOption(id=module.id, title=module.name, menu=[])
            for module in modules
        }
        module_sort_map = {module.id: module.sort for module in modules}
        grant_menu_types = {
            ResourceType.MENU.value,
            ResourceType.PAGE.value,
            ResourceType.API_GROUP.value,
        }
        for resource in resources:
            if resource.resource_type not in grant_menu_types:
                continue
            if not resource.module_id:
                continue
            module = module_map.setdefault(
                resource.module_id,
                ResourceGrantModuleOption(id=resource.module_id, title=resource.module_id, menu=[]),
            )
            parent = resource_map.get(resource.parent_id or "")
            module.menu.append(
                ResourceGrantMenuOption(
                    id=resource.id,
                    module_id=resource.module_id,
                    parent_id=resource.parent_id,
                    parent_id_name=parent.name if parent else resource.name,
                    title=resource.name,
                    button=(
                        permission_map.get(resource.id, [])
                        + child_permission_map.get(resource.id, [])
                    ),
                )
            )
        return sorted(
            [module for module in module_map.values() if module.menu],
            key=lambda item: (module_sort_map.get(item.id, 99), item.id),
        )

    async def _ensure_payload_valid(
        self,
        payload: ClientResourceCreateRequest | ClientResourceUpdateRequest,
        resource_id: str | None = None,
    ) -> None:
        """校验模块存在、编码唯一及父级关系合法。"""
        if payload.module_id and not await self.db.get(SysClientModule, payload.module_id):
            raise ConflictError("Client module does not exist")
        await self._ensure_code_unique(payload.code, payload.module_id, resource_id)
        if not payload.parent_id:
            return
        parent = await self.db.get(SysClientResource, payload.parent_id)
        if parent is None:
            raise ConflictError("Client resource parent does not exist")
        if resource_id is not None and parent.id == resource_id:
            raise ConflictError("Client resource parent cannot be itself")
        if payload.module_id and parent.module_id and parent.module_id != payload.module_id:
            raise ConflictError("Client resource parent module mismatch")

    async def _ensure_code_unique(
        self,
        code: str,
        module_id: str | None,
        resource_id: str | None = None,
    ) -> None:
        """校验资源编码在模块内唯一，重复时抛冲突错误。"""
        stmt = select(SysClientResource.id).where(
            SysClientResource.code == code,
            SysClientResource.module_id == module_id,
        )
        if resource_id is not None:
            stmt = stmt.where(SysClientResource.id != resource_id)
        if (await self.db.execute(stmt)).scalar_one_or_none() is not None:
            raise ConflictError("Client resource code already exists")
