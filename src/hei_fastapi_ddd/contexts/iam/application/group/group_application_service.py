""" Author: Charlie

账户组应用服务：账户组 CRUD、成员/角色/资源授权与数据范围可见性校验。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.exceptions.business import AuthorizationError
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, to_schema, to_schema_list
from hei_fastapi_ddd.shared.security.data_scope import (
    IAM_ACCOUNT_PAGE,
    IAM_DEPT_PAGE,
    IAM_GROUP_PAGE,
    IAM_ROLE_PAGE,
    build_data_scope_filter,
    resolve_data_scope_dept_ids,
)
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.messaging import emit
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.iam.application.account.query_service import AccountQueryService
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import AccountRepository
from hei_fastapi_ddd.contexts.iam.application.client.client_application_service import ClientResourceService
from hei_fastapi_ddd.contexts.iam.domain.enums import GrantSubjectType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.group_po import SysGroup
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.group_repository import GroupRepository
from hei_fastapi_ddd.contexts.iam.interfaces.http.group_schemas import (
    GroupAdminPageQuery,
    GroupCreateRequest,
    GroupGrantClientResourceRequest,
    GroupGrantResourceRequest,
    GroupGrantRoleRequest,
    GroupGrantUserRequest,
    GroupOwnClientResourceQuery,
    GroupOwnClientResourceResponse,
    GroupOwnResourceQuery,
    GroupOwnResourceResponse,
    GroupOwnRoleQuery,
    GroupOwnRoleResponse,
    GroupOwnUserResponse,
    GroupResourceGrantInfo,
    GroupUpdateRequest,
    SysGroupSchema,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_po import SysIamRelation
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import IamRelationRepository
from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import ResourceService
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po import SysRole
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_repository import RoleRepository
from hei_fastapi_ddd.contexts.iam.application.support import audit as iam_audit


class GroupService:
    """账户组应用服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GroupRepository(db)
        self.relation_repo = IamRelationRepository(db)

    async def create(
        self,
        payload: GroupCreateRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """创建账户组，传入 session 时校验所属部门可见性。"""
        if session is not None and payload.owner_dept_id:
            await self._ensure_depts_visible(session, "iam:group:create", [payload.owner_dept_id])
        async with transactional(self.db):
            await self.repo.create(payload)
        entity = (
            await self.db.execute(select(SysGroup).where(SysGroup.name == payload.name).limit(1))
        ).scalar_one()
        audit_snapshots.created_entity(entity)

    async def update(
        self,
        payload: GroupUpdateRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """更新账户组，传入 session 时校验账户组与所属部门可见性。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:update", [payload.id])
            if payload.owner_dept_id:
                await self._ensure_depts_visible(
                    session,
                    "iam:group:update",
                    [payload.owner_dept_id],
                )
        existing = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
        updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest, session: SessionPayload | None = None) -> None:
        """删除账户组，传入 session 时先校验可见性。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:delete", payload.ids)
        entities = await self.repo.list_by_ids(payload.ids)
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(self, query: IdQuery, session: SessionPayload | None = None) -> SysGroupSchema:
        """查询账户组详情并回显创建人昵称。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:detail", [query.id])
        schema = to_schema(SysGroupSchema, await self.repo.get_required(query.id))
        return schema

    async def page_admin(
        self,
        query: GroupAdminPageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[SysGroupSchema]:
        """分页查询账户组，叠加数据范围过滤。"""
        data_scope_filter = (
            await self._group_scope_filter(session, "iam:group:page")
            if session is not None
            else None
        )
        items, total = await self.repo.page_admin(query, data_scope_filter)
        schemas = to_schema_list(SysGroupSchema, items)
        return build_page(query, total, schemas)

    async def own_user(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> GroupOwnUserResponse:
        """返回账户组成员（含全部可见账户与已选成员）。"""
        account_filter = (
            await self._account_scope_filter(session, "iam:group:ownuser")
            if session is not None
            else None
        )
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:ownuser", [query.id])
        users = await self.repo.list_accounts(account_filter)
        group_users = await self.repo.list_group_accounts(query.id, account_filter)
        return GroupOwnUserResponse(
            id=query.id,
            users=await AccountQueryService(self.db).build_account_picker_schemas(users),
            account_ids=[account.id for account in group_users],
        )

    async def grant_user(
        self,
        payload: GroupGrantUserRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户组成员，并刷新受影响账户会话。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:grantuser", [payload.id])
            await self._ensure_accounts_visible(session, "iam:group:grantuser", payload.account_ids)
        group = await self.repo.get_required(payload.id)
        audit_snapshots.subject(group.name)
        audit_snapshots.resource_id(group.id)
        old_account_ids = await self.repo.list_account_ids_by_group(payload.id)
        audit_snapshots.before(await iam_audit.account_ids_field(self.db, old_account_ids))
        async with transactional(self.db):
            await self.repo.replace_group_accounts(payload)
        audit_snapshots.after(await iam_audit.account_ids_field(self.db, payload.account_ids))
        await self._refresh_accounts(sorted(set(old_account_ids + payload.account_ids)))

    async def own_role(
        self,
        query: GroupOwnRoleQuery,
        session: SessionPayload | None = None,
    ) -> GroupOwnRoleResponse:
        """返回账户组绑定的角色（叠加数据范围过滤）。"""
        role_filter = (
            await self._role_scope_filter(session, "iam:group:ownrole")
            if session is not None
            else None
        )
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:ownrole", [query.id])
        role_ids = await self.repo.list_group_role_ids(
            query.id,
            role_filter,
            account_type=query.account_type.value if query.account_type else None,
        )
        return GroupOwnRoleResponse(
            id=query.id,
            roles=await self.repo.list_roles_by_ids(role_ids),
            role_ids=role_ids,
        )

    async def grant_role(
        self,
        payload: GroupGrantRoleRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户组角色，并刷新成员账户会话。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:grantrole", [payload.id])
            await self._ensure_roles_visible(session, "iam:group:grantrole", payload.role_ids)
        group = await self.repo.get_required(payload.id)
        audit_snapshots.subject(group.name)
        audit_snapshots.resource_id(group.id)
        account_type = payload.account_type.value
        old_role_ids = await self.repo.list_group_role_ids(payload.id, account_type=account_type)
        audit_snapshots.before(await iam_audit.role_ids_field(self.db, old_role_ids))
        async with transactional(self.db):
            account_ids = await self.repo.list_account_ids_by_group(payload.id)
            await self.repo.replace_group_roles(payload)
        audit_snapshots.after(await iam_audit.role_ids_field(self.db, payload.role_ids))
        await self._refresh_accounts(account_ids)

    async def own_resource(
        self,
        query: GroupOwnResourceQuery,
        session: SessionPayload | None = None,
    ) -> GroupOwnResourceResponse:
        """返回账户组拥有的资源授权。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:ownresource", [query.id])
        return GroupOwnResourceResponse(
            id=query.id,
            modules=await ResourceService(self.db).list_grant_modules(
                module_client=query.account_type,
            ),
            grant_info_list=[
                GroupResourceGrantInfo.model_validate(grant)
                for grant in await self.relation_repo.list_subject_resource_grants(
                    GrantSubjectType.GROUP,
                    query.id,
                    account_type=query.account_type,
                )
            ],
        )

    async def grant_resource(
        self,
        payload: GroupGrantResourceRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户组资源授权，并刷新成员账户会话。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:grantresource", [payload.id])
        group = await self.repo.get_required(payload.id)
        audit_snapshots.subject(group.name)
        audit_snapshots.resource_id(group.id)
        old_grants = await self.relation_repo.list_subject_resource_grants(
            GrantSubjectType.GROUP,
            payload.id,
            account_type=payload.account_type,
        )
        audit_snapshots.before(await iam_audit.grant_resource_field(self.db, "资源", old_grants))
        async with transactional(self.db):
            account_ids = await self.repo.list_account_ids_by_group(payload.id)
            await self.relation_repo.replace_subject_resource_grant_infos(
                GrantSubjectType.GROUP,
                payload.id,
                payload.grant_info_list,
                account_type=payload.account_type,
            )
        new_grants = await self.relation_repo.list_subject_resource_grants(
            GrantSubjectType.GROUP,
            payload.id,
            account_type=payload.account_type,
        )
        audit_snapshots.after(await iam_audit.grant_resource_field(self.db, "资源", new_grants))
        await self._refresh_accounts(account_ids)

    async def own_client_resource(
        self,
        query: GroupOwnClientResourceQuery,
        session: SessionPayload | None = None,
    ) -> GroupOwnClientResourceResponse:
        """返回账户组拥有的客户端资源授权。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:ownclientresource", [query.id])
        return GroupOwnClientResourceResponse(
            id=query.id,
            modules=await ClientResourceService(self.db).list_grant_modules(query.account_type),
            grant_info_list=[
                GroupResourceGrantInfo.model_validate(grant)
                for grant in await self.relation_repo.list_subject_client_resource_grants(
                    GrantSubjectType.GROUP,
                    query.id,
                    account_type=query.account_type,
                )
            ],
        )

    async def grant_client_resource(
        self,
        payload: GroupGrantClientResourceRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户组客户端资源授权，并刷新成员账户会话。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:grantclientresource", [payload.id])
        group = await self.repo.get_required(payload.id)
        audit_snapshots.subject(group.name)
        audit_snapshots.resource_id(group.id)
        old_grants = await self.relation_repo.list_subject_client_resource_grants(
            GrantSubjectType.GROUP,
            payload.id,
            account_type=payload.account_type,
        )
        audit_snapshots.before(
            await iam_audit.grant_client_resource_field(self.db, "客户端资源", old_grants)
        )
        async with transactional(self.db):
            account_ids = await self.repo.list_account_ids_by_group(payload.id)
            await self.relation_repo.replace_subject_client_resource_grant_infos(
                GrantSubjectType.GROUP,
                payload.id,
                payload.grant_info_list,
                account_type=payload.account_type,
            )
        new_grants = await self.relation_repo.list_subject_client_resource_grants(
            GrantSubjectType.GROUP,
            payload.id,
            account_type=payload.account_type,
        )
        audit_snapshots.after(
            await iam_audit.grant_client_resource_field(self.db, "客户端资源", new_grants)
        )
        await self._refresh_accounts(account_ids)

    async def _refresh_accounts(self, account_ids: list[str]) -> None:
        """刷新指定账户的在线会话缓存。"""
        await emit("on_authorization_changed", account_ids=sorted(set(account_ids)))

    async def _group_scope_filter(self, session: SessionPayload, permission_key: str):
        """构造账户组数据范围过滤条件。"""
        return await build_data_scope_filter(
            self.db,
            session,
            permission_key,
            owner_column=SysGroup.created_by,
            dept_column=SysGroup.owner_dept_id,
        )

    async def _role_scope_filter(self, session: SessionPayload, permission_key: str):
        """构造角色数据范围过滤条件。"""
        return await build_data_scope_filter(
            self.db,
            session,
            permission_key,
            owner_column=SysRole.created_by,
            dept_column=SysRole.owner_dept_id,
        )

    async def _account_scope_filter(self, session: SessionPayload, permission_key: str):
        """构造账户数据范围过滤条件。"""
        return await build_data_scope_filter(
            self.db,
            session,
            permission_key,
            owner_column=SysAccount.id,
            dept_column=SysIamRelation.target_id,
        )

    async def _ensure_groups_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        group_ids: list[str],
    ) -> None:
        """校验目标账户组均在当前数据范围内，否则抛授权错误。"""
        _ = permission_key
        unique_ids = list(dict.fromkeys(group_ids))
        if not unique_ids:
            return
        data_scope_filter = await self._group_scope_filter(session, IAM_GROUP_PAGE)
        if await self.repo.count_groups_in_scope(unique_ids, data_scope_filter) != len(unique_ids):
            raise AuthorizationError("Group is outside current data scope")

    async def _ensure_roles_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        role_ids: list[str],
    ) -> None:
        """校验目标角色均在当前数据范围内，否则抛授权错误。"""
        _ = permission_key
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            return
        data_scope_filter = await self._role_scope_filter(session, IAM_ROLE_PAGE)
        count = await RoleRepository(self.db).count_roles_in_scope(unique_ids, data_scope_filter)
        if count != len(unique_ids):
            raise AuthorizationError("Role is outside current data scope")

    async def _ensure_accounts_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        account_ids: list[str],
    ) -> None:
        """校验目标账户均在当前数据范围内，否则抛授权错误。"""
        _ = permission_key
        unique_ids = list(dict.fromkeys(account_ids))
        if not unique_ids:
            return
        data_scope_filter = await self._account_scope_filter(session, IAM_ACCOUNT_PAGE)
        count = await AccountRepository(self.db).count_accounts_in_scope(
            unique_ids,
            data_scope_filter,
        )
        if count != len(unique_ids):
            raise AuthorizationError("Account is outside current data scope")

    async def _ensure_depts_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        dept_ids: list[str],
    ) -> None:
        """校验目标部门均在当前可见部门集合内，否则抛授权错误。"""
        _ = permission_key
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return
        visible_dept_ids = await resolve_data_scope_dept_ids(self.db, session, IAM_DEPT_PAGE)
        if visible_dept_ids is None:
            return
        allowed_ids = set(visible_dept_ids)
        if any(dept_id not in allowed_ids for dept_id in unique_ids):
            raise AuthorizationError("Dept is outside current data scope")
