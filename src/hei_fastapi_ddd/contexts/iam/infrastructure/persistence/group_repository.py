""" Author: Charlie

账户组仓储：账户组 CRUD 及成员、角色与资源授权的查询和替换。
"""

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.iam.domain.enums import IamRelationSubjectType, IamRelationTargetType, IamRelationType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.group_po import SysGroup
from hei_fastapi_ddd.contexts.iam.interfaces.http.group_schemas import (
    GroupAdminPageQuery,
    GroupCreateRequest,
    GroupGrantRoleRequest,
    GroupGrantUserRequest,
    GroupRoleAssignRequest,
    GroupUpdateRequest,
)
from hei_fastapi_ddd.contexts.iam.application.reference_guard import count_group_references, raise_if_referenced
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_po import SysIamRelation
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import IamRelationRepository, account_dept_condition
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po import SysRole


class GroupRepository:
    """账户组仓储。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.relations = IamRelationRepository(db)

    async def create(self, payload: GroupCreateRequest) -> None:
        """创建账户组。"""
        group = SysGroup(**payload.model_dump())
        self.db.add(group)
        await self.db.flush()

    async def get_by_id(self, group_id: str) -> SysGroup | None:
        """按主键查询账户组。"""
        return await self.db.get(SysGroup, group_id)

    async def get_required(self, group_id: str) -> SysGroup:
        """按主键查询账户组，不存在时抛 NotFoundError。"""
        entity = await self.get_by_id(group_id)
        if entity is None:
            raise NotFoundError("Group not found")
        return entity

    async def update(self, payload: GroupUpdateRequest) -> None:
        """更新账户组。"""
        entity = await self.get_required(payload.id)
        data = payload.model_dump(exclude={"id"})
        for key, value in data.items():
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, group_ids: list[str]) -> None:
        """删除账户组，存在引用时抛冲突错误。"""
        unique_ids = list(dict.fromkeys(group_ids))
        if not unique_ids:
            return
        stmt = select(SysGroup.id).where(SysGroup.id.in_(unique_ids))
        existing_ids = set((await self.db.execute(stmt)).scalars().all())
        if len(existing_ids) != len(unique_ids):
            raise NotFoundError("Group not found")
        raise_if_referenced("Group", await count_group_references(self.db, unique_ids))
        await self.db.execute(delete(SysGroup).where(SysGroup.id.in_(unique_ids)))

    async def count_groups_in_scope(
        self,
        group_ids: list[str],
        data_scope_filter: ColumnElement[bool],
    ) -> int:
        """统计处于当前数据范围内的目标账户组数量。"""
        unique_ids = list(dict.fromkeys(group_ids))
        if not unique_ids:
            return 0
        stmt = select(func.count(SysGroup.id)).where(SysGroup.id.in_(unique_ids), data_scope_filter)
        return int((await self.db.execute(stmt)).scalar_one())

    async def page_admin(
        self,
        query: GroupAdminPageQuery,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> tuple[list[SysGroup], int]:
        """按条件分页查询账户组并统计总数。"""
        stmt: Select[tuple[SysGroup]] = select(SysGroup)
        count_stmt = select(func.count(SysGroup.id))
        filters = []
        if query.name:
            filters.append(SysGroup.name.contains(query.name))
        if query.status:
            filters.append(SysGroup.status == query.status)
        if data_scope_filter is not None:
            filters.append(data_scope_filter)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysGroup.id.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        groups = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return groups, total

    async def list_by_ids(self, group_ids: list[str]) -> list[SysGroup]:
        """按 ID 列表批量查询账户组。"""
        unique_ids = list(dict.fromkeys(group_ids))
        if not unique_ids:
            return []
        stmt = select(SysGroup).where(SysGroup.id.in_(unique_ids))
        return list((await self.db.execute(stmt)).scalars().all())

    async def assign_group_to_role(self, payload: GroupRoleAssignRequest) -> SysIamRelation:
        """为账户组追加单个角色关系（账户组与角色均需存在）。"""
        if not await self.db.get(SysGroup, payload.group_id):
            raise NotFoundError("Group not found")
        if not await self.db.get(SysRole, payload.role_id):
            raise NotFoundError("Role not found")
        relation = self.relations.group_role(
            payload.group_id,
            payload.role_id,
            payload.account_type,
        )
        self.db.add(relation)
        await self.db.flush()
        return relation

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

    async def list_group_accounts(
        self,
        group_id: str,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> list[SysAccount]:
        """列出账户组的成员账户，可叠加数据范围过滤。"""
        await self.get_required(group_id)
        account_group_rel = aliased(SysIamRelation)
        stmt = (
            select(SysAccount)
            .join(account_group_rel, account_group_rel.subject_id == SysAccount.id)
            .where(
                account_group_rel.subject_type == IamRelationSubjectType.ACCOUNT.value,
                account_group_rel.relation_type == IamRelationType.ACCOUNT_GROUP.value,
                account_group_rel.target_type == IamRelationTargetType.GROUP.value,
                account_group_rel.target_id == group_id,
            )
            .order_by(SysAccount.id.desc())
        )
        if data_scope_filter is not None:
            stmt = stmt.outerjoin(
                SysIamRelation,
                account_dept_condition(SysIamRelation, SysAccount.id),
            ).where(data_scope_filter)
        return list((await self.db.execute(stmt)).unique().scalars().all())

    async def list_account_ids_by_group(self, group_id: str) -> list[str]:
        """列出账户组当前成员的账户 ID。"""
        await self.get_required(group_id)
        stmt = select(SysIamRelation.subject_id).where(
            SysIamRelation.subject_type == IamRelationSubjectType.ACCOUNT.value,
            SysIamRelation.relation_type == IamRelationType.ACCOUNT_GROUP.value,
            SysIamRelation.target_type == IamRelationTargetType.GROUP.value,
            SysIamRelation.target_id == group_id,
        )
        return [str(value) for value in (await self.db.execute(stmt)).scalars().all()]

    async def replace_group_accounts(self, payload: GroupGrantUserRequest) -> None:
        """全量替换账户组成员（先删后建，账户需全部存在）。"""
        await self.get_required(payload.id)
        account_ids = list(dict.fromkeys(payload.account_ids))
        if account_ids:
            stmt = select(SysAccount.id).where(SysAccount.id.in_(account_ids))
            existing_ids = set((await self.db.execute(stmt)).scalars().all())
            if len(existing_ids) != len(account_ids):
                raise NotFoundError("Account not found")
        await self.relations.delete_target_relations(
            IamRelationType.ACCOUNT_GROUP,
            IamRelationTargetType.GROUP.value,
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
                self.relations.account_group(
                    account_id,
                    payload.id,
                    account_type_map[account_id],
                )
            )
        await self.db.flush()

    async def list_roles_by_ids(self, role_ids: list[str]) -> list[SysRole]:
        """按 ID 列表查询角色，按排序与 ID 倒序返回。"""
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            return []
        stmt = (
            select(SysRole)
            .where(SysRole.id.in_(unique_ids))
            .order_by(SysRole.sort.asc(), SysRole.id.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_group_role_ids(
        self,
        group_id: str,
        data_scope_filter: ColumnElement[bool] | None = None,
        account_type: str | None = None,
    ) -> list[str]:
        """列出账户组绑定的角色 ID，可按账户体系与数据范围过滤。"""
        await self.get_required(group_id)
        filters = [
            SysIamRelation.subject_type == IamRelationSubjectType.GROUP.value,
            SysIamRelation.subject_id == group_id,
            SysIamRelation.relation_type == IamRelationType.GROUP_ROLE.value,
            SysIamRelation.target_type == IamRelationTargetType.ROLE.value,
        ]
        if account_type is not None:
            filters.append(SysIamRelation.account_type == account_type)
        stmt = select(SysIamRelation.target_id).where(*filters)
        if data_scope_filter is not None:
            stmt = stmt.join(SysRole, SysRole.id == SysIamRelation.target_id).where(
                data_scope_filter
            )
        return [str(value) for value in (await self.db.execute(stmt)).scalars().all()]

    async def replace_group_roles(self, payload: GroupGrantRoleRequest) -> None:
        """全量替换账户组的角色关系（先删后建，角色需全部存在）。"""
        await self.get_required(payload.id)
        role_ids = list(dict.fromkeys(payload.role_ids))
        if role_ids:
            stmt = select(SysRole.id).where(SysRole.id.in_(role_ids))
            existing_ids = set((await self.db.execute(stmt)).scalars().all())
            if len(existing_ids) != len(role_ids):
                raise NotFoundError("Role not found")
        account_type = payload.account_type.value
        await self.relations.delete_subject_relations(
            IamRelationSubjectType.GROUP.value,
            payload.id,
            IamRelationType.GROUP_ROLE,
            account_type=account_type,
        )
        for role_id in role_ids:
            self.db.add(self.relations.group_role(payload.id, role_id, account_type))
        await self.db.flush()
