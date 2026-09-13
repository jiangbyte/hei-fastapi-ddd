""" Author: Charlie

角色应用服务：角色 CRUD、内置角色保护、授权与数据范围可见性校验。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.persistence.batch import chunked
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.exceptions.business import AuthorizationError, BusinessError, NotFoundError
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, to_schema, to_schema_list
from hei_fastapi_ddd.shared.security.data_scope import (
    IAM_ACCOUNT_PAGE,
    IAM_DEPT_PAGE,
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
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_po import SysIamRelation
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import IamRelationRepository
from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import ResourceService
from hei_fastapi_ddd.contexts.iam.domain.role.constants import SUPER_ADMIN_ROLE_CODE
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po import SysRole
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_repository import RoleRepository
from hei_fastapi_ddd.contexts.iam.interfaces.http.role_schemas import (
    RoleAdminPageQuery,
    RoleCreateRequest,
    RoleGrantClientResourceRequest,
    RoleGrantResourceRequest,
    RoleGrantUserRequest,
    RoleOwnClientResourceQuery,
    RoleOwnClientResourceResponse,
    RoleOwnResourceQuery,
    RoleOwnResourceResponse,
    RoleOwnUserResponse,
    RoleResourceGrantInfo,
    RoleUpdateRequest,
    SysRoleSchema,
)
from hei_fastapi_ddd.contexts.iam.application.support import audit as iam_audit
from hei_fastapi_ddd.contexts.profile.application.utils.profile import get_profiles_batch


class RoleService:
    """角色应用服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RoleRepository(db)

    async def create(
        self,
        payload: RoleCreateRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """创建角色，传入 session 时校验所属部门可见性；编码需唯一（对齐 hei-boot）。"""
        if await self.repo.get_by_code(payload.code) is not None:
            raise BusinessError("Role code already exists")
        if session is not None and payload.owner_dept_id:
            await self._ensure_depts_visible(session, "iam:role:create", [payload.owner_dept_id])
        async with transactional(self.db):
            await self.repo.create(payload)
        entity = await self.repo.get_by_code(payload.code)
        if entity is not None:
            audit_snapshots.created_entity(entity)

    async def update(
        self,
        payload: RoleUpdateRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """更新角色，传入 session 时校验可见性并保护内置角色。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:update", [payload.id])
            if payload.owner_dept_id:
                await self._ensure_depts_visible(
                    session,
                    "iam:role:update",
                    [payload.owner_dept_id],
                )
        existing = await self.repo.get_required(payload.id)
        self._ensure_protected_role_mutable(existing, payload)
        duplicate = await self.repo.get_by_code(payload.code)
        if duplicate is not None and duplicate.id != payload.id:
            raise BusinessError("Role code already exists")
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
        updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest, session: SessionPayload | None = None) -> None:
        """删除角色，传入 session 时校验可见性并阻止删除内置角色。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:delete", payload.ids)
        await self._ensure_roles_deletable(payload.ids)
        entities = await self.repo.list_by_ids(payload.ids)
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(self, query: IdQuery, session: SessionPayload | None = None) -> SysRoleSchema:
        """查询角色详情并回显部门名称与创建人昵称。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:detail", [query.id])
        schema = to_schema(SysRoleSchema, await self.repo.get_required(query.id))
        await self._resolve_names([schema])
        return schema

    async def page_admin(
        self,
        query: RoleAdminPageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[SysRoleSchema]:
        """分页查询角色，叠加数据范围过滤。"""
        data_scope_filter = (
            await self._role_scope_filter(session, "iam:role:page") if session is not None else None
        )
        items, total = await self.repo.page_admin(query, data_scope_filter)
        schemas = to_schema_list(SysRoleSchema, items)
        await self._resolve_names(schemas)
        return build_page(query, total, schemas)

    async def own_resource(
        self,
        query: RoleOwnResourceQuery,
        session: SessionPayload | None = None,
    ) -> RoleOwnResourceResponse:
        """返回角色拥有的资源授权。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:ownresource", [query.id])
        return RoleOwnResourceResponse(
            id=query.id,
            modules=await ResourceService(self.db).list_grant_modules(
                module_client=query.account_type,
            ),
            grant_info_list=await self.repo.list_resource_grants(
                query.id,
                account_type=query.account_type.value if query.account_type else None,
            ),
        )

    async def grant_resource(
        self,
        payload: RoleGrantResourceRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换角色资源授权，并刷新成员账户会话。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:grantresource", [payload.id])
        role = await self.repo.get_required(payload.id)
        audit_snapshots.subject(role.name)
        audit_snapshots.resource_id(role.id)
        account_type = payload.account_type.value
        old_grants = await self.repo.list_resource_grants(payload.id, account_type=account_type)
        audit_snapshots.before(await iam_audit.grant_resource_field(self.db, "资源", old_grants))
        async with transactional(self.db):
            old_account_ids = await self.repo.list_account_ids_by_role(payload.id)
            await self.repo.replace_resource_grants(payload)
        new_grants = await self.repo.list_resource_grants(payload.id, account_type=account_type)
        audit_snapshots.after(await iam_audit.grant_resource_field(self.db, "资源", new_grants))
        await self._refresh_accounts(old_account_ids)

    async def own_client_resource(
        self,
        query: RoleOwnClientResourceQuery,
        session: SessionPayload | None = None,
    ) -> RoleOwnClientResourceResponse:
        """返回角色拥有的客户端资源授权。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:ownclientresource", [query.id])
        grants = await IamRelationRepository(self.db).list_subject_client_resource_grants(
            GrantSubjectType.ROLE,
            query.id,
            account_type=query.account_type,
        )
        return RoleOwnClientResourceResponse(
            id=query.id,
            modules=await ClientResourceService(self.db).list_grant_modules(query.account_type),
            grant_info_list=[RoleResourceGrantInfo.model_validate(grant) for grant in grants],
        )

    async def grant_client_resource(
        self,
        payload: RoleGrantClientResourceRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换角色客户端资源授权，并刷新成员账户会话。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:grantclientresource", [payload.id])
        role = await self.repo.get_required(payload.id)
        audit_snapshots.subject(role.name)
        audit_snapshots.resource_id(role.id)
        account_type = payload.account_type.value
        relation_repo = IamRelationRepository(self.db)
        old_grants = await relation_repo.list_subject_client_resource_grants(
            GrantSubjectType.ROLE,
            payload.id,
            account_type=account_type,
        )
        audit_snapshots.before(
            await iam_audit.grant_client_resource_field(self.db, "客户端资源", old_grants)
        )
        async with transactional(self.db):
            old_account_ids = await self.repo.list_account_ids_by_role(payload.id)
            await relation_repo.replace_subject_client_resource_grant_infos(
                GrantSubjectType.ROLE,
                payload.id,
                payload.grant_info_list,
                account_type=payload.account_type,
            )
        new_grants = await relation_repo.list_subject_client_resource_grants(
            GrantSubjectType.ROLE,
            payload.id,
            account_type=account_type,
        )
        audit_snapshots.after(
            await iam_audit.grant_client_resource_field(self.db, "客户端资源", new_grants)
        )
        await self._refresh_accounts(old_account_ids)

    async def own_user(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> RoleOwnUserResponse:
        """返回拥有该角色的用户（含全部可见账户与已选成员）。"""
        account_filter = (
            await self._account_scope_filter(session, "iam:role:ownuser")
            if session is not None
            else None
        )
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:ownuser", [query.id])
        users = await self.repo.list_accounts(account_filter)
        role_users = await self.repo.list_role_accounts(query.id, account_filter)
        return RoleOwnUserResponse(
            id=query.id,
            users=await AccountQueryService(self.db).build_account_picker_schemas(users),
            account_ids=[account.id for account in role_users],
        )

    async def grant_user(
        self,
        payload: RoleGrantUserRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换角色成员，并刷新受影响账户会话。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:grantuser", [payload.id])
            await self._ensure_accounts_visible(session, "iam:role:grantuser", payload.account_ids)
        role = await self.repo.get_required(payload.id)
        audit_snapshots.subject(role.name)
        audit_snapshots.resource_id(role.id)
        old_account_ids = await self.repo.list_account_ids_by_role(payload.id)
        audit_snapshots.before(await iam_audit.account_ids_field(self.db, old_account_ids))
        async with transactional(self.db):
            await self.repo.replace_role_accounts(payload)
        audit_snapshots.after(await iam_audit.account_ids_field(self.db, payload.account_ids))
        await self._refresh_accounts(sorted(set(old_account_ids + payload.account_ids)))

    async def _resolve_names(self, dtos: list[SysRoleSchema]) -> None:
        """批量解析部门名称和创建人/更新人昵称。"""
        dept_ids = {d.owner_dept_id for d in dtos if d.owner_dept_id}
        creator_ids = set()
        for d in dtos:
            if d.created_by:
                creator_ids.add(d.created_by)
            if d.updated_by:
                creator_ids.add(d.updated_by)
        if dept_ids:
            dept_map = await self.repo.resolve_dept_names(list(dept_ids))
            for d in dtos:
                if d.owner_dept_id and d.owner_dept_id in dept_map:
                    d.owner_dept_name = dept_map[d.owner_dept_id]
        if creator_ids:
            profiles = await get_profiles_batch(self.db, AccountType.ADMIN, list(creator_ids))
            for d in dtos:
                if d.created_by and d.created_by in profiles:
                    d.created_name = getattr(profiles[d.created_by], "nickname", None)
                if d.updated_by and d.updated_by in profiles:
                    d.updated_name = getattr(profiles[d.updated_by], "nickname", None)

    async def _refresh_accounts(self, account_ids: list[str]) -> None:
        """刷新指定账户的在线会话缓存。"""
        await emit("on_authorization_changed", account_ids=sorted(set(account_ids)))

    def _is_protected_role(self, role: SysRole) -> bool:
        """判断角色是否为内置或超级管理员角色。"""
        return bool(role.is_builtin) or role.code == SUPER_ADMIN_ROLE_CODE

    def _ensure_protected_role_mutable(
        self,
        existing: SysRole,
        payload: RoleUpdateRequest,
    ) -> None:
        """阻止修改内置/超级管理员角色的编码与内置标记。"""
        if not self._is_protected_role(existing):
            return
        if payload.code != existing.code:
            raise BusinessError("Cannot change code of builtin or SUPER_ADMIN role")
        if bool(payload.is_builtin) != bool(existing.is_builtin):
            raise BusinessError("Cannot change is_builtin of builtin or SUPER_ADMIN role")

    async def _ensure_roles_deletable(self, role_ids: list[str]) -> None:
        """阻止删除内置或超级管理员角色（分批 IN 查询，避免逐条查询）。"""
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            return
        roles: list[SysRole] = []
        for batch in chunked(unique_ids):
            roles.extend(await self.repo.list_by_ids(batch))
        if len(roles) != len(unique_ids):
            raise NotFoundError("Role not found")
        for role in roles:
            if self._is_protected_role(role):
                raise BusinessError("Cannot delete builtin or SUPER_ADMIN role")

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
        if await self.repo.count_roles_in_scope(unique_ids, data_scope_filter) != len(unique_ids):
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
