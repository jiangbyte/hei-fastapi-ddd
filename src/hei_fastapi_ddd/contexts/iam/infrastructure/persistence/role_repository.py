""" Author: Charlie

角色仓储：角色 CRUD、资源授权与成员账户关系的查询和替换。
"""

from collections import defaultdict

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from hei_fastapi_ddd.shared.persistence.compat import like_contains
from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.dept_po import SysDept
from hei_fastapi_ddd.contexts.iam.domain.enums import (
    GrantMode,
    GrantSubjectType,
    IamRelationSubjectType,
    IamRelationTargetType,
    IamRelationType,
    ResourceType,
)
from hei_fastapi_ddd.contexts.iam.application.reference_guard import count_role_references, raise_if_referenced
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_po import SysIamRelation
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import IamRelationRepository, account_dept_condition
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po import SysRole
from hei_fastapi_ddd.contexts.iam.interfaces.http.role_schemas import (
    RoleAdminPageQuery,
    RoleCreateRequest,
    RoleGrantResourceRequest,
    RoleGrantUserRequest,
    RoleResourceGrantInfo,
    RoleUpdateRequest,
)


class RoleRepository:
    """角色仓储。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.relations = IamRelationRepository(db)

    async def create(self, payload: RoleCreateRequest) -> None:
        """创建角色。"""
        role = SysRole(**payload.model_dump())
        self.db.add(role)
        await self.db.flush()

    async def get_by_id(self, role_id: str) -> SysRole | None:
        """按主键查询角色。"""
        return await self.db.get(SysRole, role_id)

    async def get_by_code(self, code: str) -> SysRole | None:
        """按角色编码查询角色（编码唯一性预校验）。"""
        stmt = select(SysRole).where(SysRole.code == code).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_required(self, role_id: str) -> SysRole:
        """按主键查询角色，不存在时抛 NotFoundError。"""
        entity = await self.get_by_id(role_id)
        if entity is None:
            raise NotFoundError("Role not found")
        return entity

    async def update(self, payload: RoleUpdateRequest) -> None:
        """更新角色。"""
        entity = await self.get_required(payload.id)
        data = payload.model_dump(exclude={"id"})
        for key, value in data.items():
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, role_ids: list[str]) -> None:
        """删除角色，存在引用时抛冲突错误。"""
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            return
        stmt = select(SysRole.id).where(SysRole.id.in_(unique_ids))
        existing_ids = set((await self.db.execute(stmt)).scalars().all())
        if len(existing_ids) != len(unique_ids):
            raise NotFoundError("Role not found")
        raise_if_referenced("Role", await count_role_references(self.db, unique_ids))
        await self.db.execute(delete(SysRole).where(SysRole.id.in_(unique_ids)))

    async def count_roles_in_scope(
        self,
        role_ids: list[str],
        data_scope_filter: ColumnElement[bool],
    ) -> int:
        """统计处于当前数据范围内的目标角色数量。"""
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            return 0
        stmt = select(func.count(SysRole.id)).where(SysRole.id.in_(unique_ids), data_scope_filter)
        return int((await self.db.execute(stmt)).scalar_one())

    async def page_admin(
        self,
        query: RoleAdminPageQuery,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> tuple[list[SysRole], int]:
        """按条件分页查询角色并统计总数。"""
        stmt: Select[tuple[SysRole]] = select(SysRole)
        count_stmt = select(func.count(SysRole.id))
        filters = []
        if query.code:
            filters.append(like_contains(SysRole.code, query.code))
        if query.name:
            filters.append(like_contains(SysRole.name, query.name))
        if query.category:
            filters.append(SysRole.category == query.category)
        if query.scope_type:
            filters.append(SysRole.scope_type == query.scope_type.value)
        if query.status:
            filters.append(SysRole.status == query.status)
        if data_scope_filter is not None:
            filters.append(data_scope_filter)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysRole.sort.asc(), SysRole.id.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        roles = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return roles, total

    async def list_by_ids(self, role_ids: list[str]) -> list[SysRole]:
        """按 ID 列表批量查询角色。"""
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            return []
        stmt = select(SysRole).where(SysRole.id.in_(unique_ids))
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_resource_grants(
        self,
        role_id: str,
        account_type: str | None = None,
    ) -> list[RoleResourceGrantInfo]:
        """列出角色的资源授权明细（按钮权限归并到父菜单）。"""
        await self.get_required(role_id)
        filters = [
            SysIamRelation.subject_type == GrantSubjectType.ROLE.value,
            SysIamRelation.subject_id == role_id,
            SysIamRelation.relation_type == IamRelationType.SUBJECT_RESOURCE_GRANT.value,
            SysIamRelation.target_type == IamRelationTargetType.RESOURCE.value,
        ]
        if account_type is not None:
            filters.append(SysIamRelation.account_type == account_type)
        stmt = (
            select(SysIamRelation)
            .where(*filters)
            .order_by(SysIamRelation.id.asc())
        )
        grants = list((await self.db.execute(stmt)).scalars().all())
        resource_ids = [grant.target_id for grant in grants]
        if not resource_ids:
            return []

        resource_stmt = select(SysResource).where(SysResource.id.in_(resource_ids))
        resources = list((await self.db.execute(resource_stmt)).scalars().all())
        resource_map = {resource.id: resource for resource in resources}

        permission_filters = [
            SysIamRelation.subject_type == IamRelationSubjectType.RESOURCE.value,
            SysIamRelation.relation_type == IamRelationType.RESOURCE_PERMISSION.value,
            SysIamRelation.target_type == IamRelationTargetType.PERMISSION.value,
            SysIamRelation.subject_id.in_(resource_ids),
        ]
        if account_type is not None:
            permission_filters.append(SysIamRelation.account_type == account_type)
        permission_stmt = select(SysIamRelation).where(*permission_filters)
        permissions = list((await self.db.execute(permission_stmt)).scalars().all())
        permission_map: dict[str, list[str]] = defaultdict(list)
        for permission in permissions:
            permission_map[permission.subject_id].append(permission.target_key)

        menu_resource_ids = set()
        for resource_id in resource_ids:
            resource = resource_map.get(resource_id)
            if not resource:
                continue
            if resource.resource_type in {ResourceType.BUTTON.value, ResourceType.ACTION.value}:
                menu_resource_ids.add(resource.parent_id or resource.id)
            else:
                menu_resource_ids.add(resource.id)

        grant_map: dict[str, set[str]] = defaultdict(set)
        for resource_id in menu_resource_ids:
            grant_map[resource_id]
        for resource_id in resource_ids:
            resource = resource_map.get(resource_id)
            if not resource:
                continue
            permission_keys = permission_map.get(resource.id) or [resource.code]
            if resource.resource_type in {ResourceType.BUTTON.value, ResourceType.ACTION.value}:
                parent_id = resource.parent_id or resource.id
                grant_map[parent_id].update(permission_keys)

        return [
            RoleResourceGrantInfo(
                resource_id=resource_id,
                permission_keys=sorted(permission_keys),
            )
            for resource_id, permission_keys in sorted(grant_map.items())
        ]

    async def replace_resource_grants(self, payload: RoleGrantResourceRequest) -> None:
        """全量替换角色资源授权，权限码自动展开为对应资源并写入级联授权。"""
        await self.get_required(payload.id)
        resource_ids = list(dict.fromkeys(item.resource_id for item in payload.grant_info_list))
        original_resource_ids = set(resource_ids)
        permission_keys = list(
            dict.fromkeys(
                permission_key
                for item in payload.grant_info_list
                for permission_key in item.permission_keys
            )
        )
        if resource_ids:
            stmt = select(SysResource.id).where(SysResource.id.in_(resource_ids))
            existing_ids = set((await self.db.execute(stmt)).scalars().all())
            if len(existing_ids) != len(resource_ids):
                raise NotFoundError("Resource not found")
        account_type = payload.account_type.value
        if permission_keys:
            permission_resource_stmt = select(
                SysIamRelation.target_key,
                SysIamRelation.subject_id,
            ).where(
                SysIamRelation.subject_type == IamRelationSubjectType.RESOURCE.value,
                SysIamRelation.relation_type == IamRelationType.RESOURCE_PERMISSION.value,
                SysIamRelation.target_type == IamRelationTargetType.PERMISSION.value,
                SysIamRelation.account_type == account_type,
                SysIamRelation.target_key.in_(permission_keys),
            )
            permission_resource_rows = list((await self.db.execute(permission_resource_stmt)).all())
            code_resource_stmt = select(SysResource.code, SysResource.id).where(
                SysResource.code.in_(permission_keys),
                SysResource.resource_type.in_(
                    [ResourceType.BUTTON.value, ResourceType.ACTION.value]
                ),
            )
            code_resource_rows = list((await self.db.execute(code_resource_stmt)).all())
            permission_resource_map: dict[str, set[str]] = defaultdict(set)
            for permission_key, resource_id in permission_resource_rows:
                permission_resource_map[str(permission_key)].add(str(resource_id))
            for permission_key, resource_id in code_resource_rows:
                permission_resource_map[str(permission_key)].add(str(resource_id))
            missing_permission_keys = [
                permission_key
                for permission_key in permission_keys
                if permission_key not in permission_resource_map
            ]
            if missing_permission_keys:
                raise NotFoundError("Permission resource not found")
            for permission_key in permission_keys:
                resource_ids.extend(permission_resource_map[permission_key])
        resource_ids = list(dict.fromkeys(resource_ids))
        await self.relations.delete_subject_relations(
            GrantSubjectType.ROLE.value,
            payload.id,
            IamRelationType.SUBJECT_RESOURCE_GRANT,
            account_type=account_type,
        )
        for resource_id in resource_ids:
            grant_mode = (
                GrantMode.CASCADE.value
                if resource_id not in original_resource_ids
                else GrantMode.DIRECT.value
            )
            self.db.add(
                self.relations.subject_resource_grant(
                    GrantSubjectType.ROLE,
                    payload.id,
                    resource_id,
                    account_type,
                    GrantMode(grant_mode),
                )
            )
        await self.db.flush()

    async def list_role_accounts(
        self,
        role_id: str,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> list[SysAccount]:
        """列出拥有该角色的账户，可叠加数据范围过滤。"""
        await self.get_required(role_id)
        account_role_rel = aliased(SysIamRelation)
        stmt = (
            select(SysAccount)
            .join(account_role_rel, account_role_rel.subject_id == SysAccount.id)
            .where(
                account_role_rel.subject_type == IamRelationSubjectType.ACCOUNT.value,
                account_role_rel.relation_type == IamRelationType.ACCOUNT_ROLE.value,
                account_role_rel.target_type == IamRelationTargetType.ROLE.value,
                account_role_rel.target_id == role_id,
            )
            .order_by(SysAccount.id.desc())
        )
        if data_scope_filter is not None:
            stmt = stmt.outerjoin(
                SysIamRelation,
                account_dept_condition(SysIamRelation, SysAccount.id),
            ).where(data_scope_filter)
        return list((await self.db.execute(stmt)).unique().scalars().all())

    async def list_accounts(
        self,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> list[SysAccount]:
        """列出账户，可按数据范围过滤。"""
        stmt = select(SysAccount).order_by(SysAccount.id.desc())
        if data_scope_filter is not None:
            stmt = stmt.outerjoin(
                SysIamRelation, account_dept_condition(SysIamRelation, SysAccount.id)
            ).where(data_scope_filter)
        return list((await self.db.execute(stmt)).unique().scalars().all())

    async def replace_role_accounts(self, payload: RoleGrantUserRequest) -> None:
        """全量替换角色的账户成员（先删后建，账户需全部存在）。"""
        await self.get_required(payload.id)
        account_ids = list(dict.fromkeys(payload.account_ids))
        if account_ids:
            stmt = select(SysAccount.id).where(SysAccount.id.in_(account_ids))
            existing_ids = set((await self.db.execute(stmt)).scalars().all())
            if len(existing_ids) != len(account_ids):
                raise NotFoundError("Account not found")
        await self.relations.delete_target_relations(
            IamRelationType.ACCOUNT_ROLE,
            IamRelationTargetType.ROLE.value,
            [payload.id],
        )
        accounts = list(
            (
                await self.db.execute(
                    select(SysAccount).where(SysAccount.id.in_(account_ids))
                )
            )
            .scalars()
            .all()
        ) if account_ids else []
        account_type_map = {account.id: account.account_type for account in accounts}
        for account_id in account_ids:
            self.db.add(
                self.relations.account_role(
                    account_id,
                    payload.id,
                    account_type_map[account_id],
                )
            )
        await self.db.flush()

    async def resolve_dept_names(self, dept_ids: list[str]) -> dict[str, str]:
        """批量查询部门名称，返回 {dept_id: name} 映射。"""
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return {}
        stmt = select(SysDept.id, SysDept.name).where(SysDept.id.in_(unique_ids))
        rows = (await self.db.execute(stmt)).all()
        return {row[0]: row[1] for row in rows}

    async def list_account_ids_by_role(self, role_id: str) -> list[str]:
        """列出角色当前成员的账户 ID。"""
        stmt = select(SysIamRelation.subject_id).where(
            SysIamRelation.subject_type == IamRelationSubjectType.ACCOUNT.value,
            SysIamRelation.relation_type == IamRelationType.ACCOUNT_ROLE.value,
            SysIamRelation.target_type == IamRelationTargetType.ROLE.value,
            SysIamRelation.target_id == role_id,
        )
        return [str(value) for value in (await self.db.execute(stmt)).scalars().all()]
