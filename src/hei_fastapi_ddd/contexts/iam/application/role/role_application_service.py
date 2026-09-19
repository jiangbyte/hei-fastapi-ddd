"""Author: Charlie

角色应用服务：依赖 domain 仓储端口，不依赖 infrastructure / api。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.client.client_application_service import (
    ClientResourceService,
)
from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import (
    ResourceService,
)
from hei_fastapi_ddd.contexts.iam.application.role.dto import (
    RoleCreateCommand,
    RoleGrantClientResourceCommand,
    RoleGrantResourceCommand,
    RoleGrantUserCommand,
    RoleOwnClientResourceQuery,
    RoleOwnResourceQuery,
    RolePageQuery,
    RoleUpdateCommand,
)
from hei_fastapi_ddd.contexts.iam.application.support.audit_port import IamAuditPort
from hei_fastapi_ddd.contexts.iam.domain.account.repository import AccountRepository
from hei_fastapi_ddd.contexts.iam.domain.enums import GrantSubjectType
from hei_fastapi_ddd.contexts.iam.domain.relation.repository import IamRelationRepositoryPort
from hei_fastapi_ddd.contexts.iam.domain.role.constants import SUPER_ADMIN_ROLE_CODE
from hei_fastapi_ddd.contexts.iam.domain.role.repository import RoleRepository
from hei_fastapi_ddd.contexts.profile.application.api.profile_read_port import ProfileReadPort
from hei_fastapi_ddd.contexts.profile.application.utils.profile import get_profiles_batch
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.messaging import emit
from hei_fastapi_ddd.shared.persistence.batch import chunked
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.data_scope import IAM_ACCOUNT_PAGE, IAM_DEPT_PAGE, IAM_ROLE_PAGE
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import (
    AuthorizationError,
    BusinessError,
    NotFoundError,
)


class RoleService:
    """角色应用服务。"""

    def __init__(
        self,
        db: AsyncSession,
        audit: IamAuditPort,
        *,
        repo: RoleRepository,
        relation_repo: IamRelationRepositoryPort,
        resource_service: ResourceService,
        client_resource_service: ClientResourceService,
        account_repo: AccountRepository,
        profile_read_port: ProfileReadPort,
    ):
        self.db = db
        self.audit = audit
        self.repo = repo
        self.relation_repo = relation_repo
        self.resource_service = resource_service
        self.client_resource_service = client_resource_service
        self.account_repo = account_repo
        self._profile_read_port = profile_read_port

    async def create(
        self,
        command: RoleCreateCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """创建角色，传入 session 时校验所属部门可见性。"""
        if await self.repo.get_by_code(command.code) is not None:
            raise BusinessError("Role code already exists")
        if session is not None and command.owner_dept_id:
            await self._ensure_depts_visible(session, "iam:role:create", [command.owner_dept_id])
        async with transactional(self.db):
            await self.repo.create(command.model_dump())
        entity = await self.repo.get_by_code(command.code)
        if entity is not None:
            audit_snapshots.created_entity(entity)

    async def update(
        self,
        command: RoleUpdateCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """更新角色，传入 session 时校验可见性并保护内置角色。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:update", [command.id])
            if command.owner_dept_id:
                await self._ensure_depts_visible(
                    session,
                    "iam:role:update",
                    [command.owner_dept_id],
                )
        existing = await self.repo.get_required(command.id)
        self._ensure_protected_role_mutable(existing, command)
        duplicate = await self.repo.get_by_code(command.code)
        if duplicate is not None and duplicate["id"] != command.id:
            raise BusinessError("Role code already exists")
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(command.model_dump())
        updated = await self.repo.get_required(command.id)
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

    async def detail(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """查询角色详情行（含部门名称与创建人昵称）。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:detail", [query.id])
        row = await self.repo.get_required(query.id)
        return (await self._enrich_rows([row]))[0]

    async def page_admin(
        self,
        query: RolePageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[dict]:
        """分页查询角色，叠加数据范围过滤。"""
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
            session=session,
        )
        enriched = await self._enrich_rows(items)
        return build_page(query, total, enriched)  # type: ignore[arg-type]

    async def own_resource(
        self,
        query: RoleOwnResourceQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回角色拥有的资源授权视图。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:ownresource", [query.id])
        account_type = query.account_type.value if query.account_type else None
        return {
            "id": query.id,
            "modules": await self.resource_service.list_grant_modules(
                module_client=query.account_type,
            ),
            "grant_info_list": await self.repo.list_resource_grants(
                query.id,
                account_type=account_type,
            ),
        }

    async def grant_resource(
        self,
        command: RoleGrantResourceCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换角色资源授权，并刷新成员账户会话。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:grantresource", [command.id])
        role = await self.repo.get_required(command.id)
        audit_snapshots.subject(role["name"])
        audit_snapshots.resource_id(role["id"])
        account_type = command.account_type.value
        old_grants = await self.repo.list_resource_grants(command.id, account_type=account_type)
        audit_snapshots.before(await self.audit.grant_resource_field("资源", old_grants))
        async with transactional(self.db):
            old_account_ids = await self.repo.list_account_ids_by_role(command.id)
            await self.repo.replace_resource_grants(command.model_dump())
        new_grants = await self.repo.list_resource_grants(command.id, account_type=account_type)
        audit_snapshots.after(await self.audit.grant_resource_field("资源", new_grants))
        await self._refresh_accounts(old_account_ids)

    async def own_client_resource(
        self,
        query: RoleOwnClientResourceQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回角色拥有的客户端资源授权视图。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:ownclientresource", [query.id])
        grants = await self.relation_repo.list_subject_client_resource_grants(
            GrantSubjectType.ROLE,
            query.id,
            account_type=query.account_type,
        )
        return {
            "id": query.id,
            "modules": await self.client_resource_service.list_grant_modules(query.account_type),
            "grant_info_list": grants,
        }

    async def grant_client_resource(
        self,
        command: RoleGrantClientResourceCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换角色客户端资源授权，并刷新成员账户会话。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:grantclientresource", [command.id])
        role = await self.repo.get_required(command.id)
        audit_snapshots.subject(role["name"])
        audit_snapshots.resource_id(role["id"])
        account_type = command.account_type.value
        old_grants = await self.relation_repo.list_subject_client_resource_grants(
            GrantSubjectType.ROLE,
            command.id,
            account_type=account_type,
        )
        audit_snapshots.before(
            await self.audit.grant_client_resource_field("客户端资源", old_grants)
        )
        async with transactional(self.db):
            old_account_ids = await self.repo.list_account_ids_by_role(command.id)
            await self.relation_repo.replace_subject_client_resource_grant_infos(
                GrantSubjectType.ROLE,
                command.id,
                command.grant_info_list,
                account_type=command.account_type,
            )
        new_grants = await self.relation_repo.list_subject_client_resource_grants(
            GrantSubjectType.ROLE,
            command.id,
            account_type=account_type,
        )
        audit_snapshots.after(
            await self.audit.grant_client_resource_field("客户端资源", new_grants)
        )
        await self._refresh_accounts(old_account_ids)

    async def own_user(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回拥有该角色的用户（含全部可见账户与已选成员）。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:ownuser", [query.id])
        users = await self.repo.list_accounts(session=session)
        role_users = await self.repo.list_role_accounts(query.id, session=session)
        return {
            "id": query.id,
            "users": users,
            "account_ids": [account["id"] for account in role_users],
        }

    async def grant_user(
        self,
        command: RoleGrantUserCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换角色成员，并刷新受影响账户会话。"""
        if session is not None:
            await self._ensure_roles_visible(session, "iam:role:grantuser", [command.id])
            await self._ensure_accounts_visible(session, "iam:role:grantuser", command.account_ids)
        role = await self.repo.get_required(command.id)
        audit_snapshots.subject(role["name"])
        audit_snapshots.resource_id(role["id"])
        old_account_ids = await self.repo.list_account_ids_by_role(command.id)
        audit_snapshots.before(await self.audit.account_ids_field(old_account_ids))
        async with transactional(self.db):
            await self.repo.replace_role_accounts(command.model_dump())
        audit_snapshots.after(await self.audit.account_ids_field(command.account_ids))
        await self._refresh_accounts(sorted(set(old_account_ids + command.account_ids)))

    async def _enrich_rows(self, rows: list[dict]) -> list[dict]:
        """批量解析部门名称和创建人/更新人昵称。"""
        dept_ids = {str(r["owner_dept_id"]) for r in rows if r.get("owner_dept_id")}
        creator_ids: set[str] = set()
        for row in rows:
            if row.get("created_by"):
                creator_ids.add(str(row["created_by"]))
            if row.get("updated_by"):
                creator_ids.add(str(row["updated_by"]))
        dept_map = await self.repo.resolve_dept_names(list(dept_ids)) if dept_ids else {}
        profile_map = (
            await get_profiles_batch(
                self._profile_read_port, AccountType.ADMIN, list(creator_ids)
            )
            if creator_ids
            else {}
        )
        enriched: list[dict] = []
        for row in rows:
            item = dict(row)
            oid = item.get("owner_dept_id")
            if oid and str(oid) in dept_map:
                item["owner_dept_name"] = dept_map[str(oid)]
            cb = item.get("created_by")
            if cb and cb in profile_map:
                item["created_name"] = profile_map[cb].get("nickname")
            ub = item.get("updated_by")
            if ub and ub in profile_map:
                item["updated_name"] = profile_map[ub].get("nickname")
            enriched.append(item)
        return enriched

    async def _refresh_accounts(self, account_ids: list[str]) -> None:
        """刷新指定账户的在线会话缓存。"""
        await emit("on_authorization_changed", account_ids=sorted(set(account_ids)))

    def _is_protected_role(self, role: dict) -> bool:
        """判断角色是否为内置或超级管理员角色。"""
        return bool(role.get("is_builtin")) or role.get("code") == SUPER_ADMIN_ROLE_CODE

    def _ensure_protected_role_mutable(
        self,
        existing: dict,
        command: RoleUpdateCommand,
    ) -> None:
        """阻止修改内置/超级管理员角色的编码与内置标记。"""
        if not self._is_protected_role(existing):
            return
        if command.code != existing["code"]:
            raise BusinessError("Cannot change code of builtin or SUPER_ADMIN role")
        if bool(command.is_builtin) != bool(existing.get("is_builtin")):
            raise BusinessError("Cannot change is_builtin of builtin or SUPER_ADMIN role")

    async def _ensure_roles_deletable(self, role_ids: list[str]) -> None:
        """阻止删除内置或超级管理员角色。"""
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            return
        roles: list[dict] = []
        for batch in chunked(unique_ids):
            roles.extend(await self.repo.list_by_ids(batch))
        if len(roles) != len(unique_ids):
            raise NotFoundError("Role not found")
        for role in roles:
            if self._is_protected_role(role):
                raise BusinessError("Cannot delete builtin or SUPER_ADMIN role")

    async def _ensure_roles_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        role_ids: list[str],
    ) -> None:
        """校验目标角色均在当前数据范围内。"""
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            return
        count = await self.repo.count_roles_in_scope(
            unique_ids,
            session=session,
            permission=permission_key or IAM_ROLE_PAGE,
        )
        if count != len(unique_ids):
            raise AuthorizationError("Role is outside current data scope")

    async def _ensure_accounts_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        account_ids: list[str],
    ) -> None:
        """校验目标账户均在当前数据范围内。"""
        unique_ids = list(dict.fromkeys(account_ids))
        if not unique_ids:
            return
        count = await self.account_repo.count_accounts_in_scope(
            unique_ids,
            session=session,
            permission=permission_key or IAM_ACCOUNT_PAGE,
        )
        if count != len(unique_ids):
            raise AuthorizationError("Account is outside current data scope")

    async def _ensure_depts_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        dept_ids: list[str],
    ) -> None:
        """校验目标部门均在当前可见部门集合内。"""
        from hei_fastapi_ddd.shared.security.data_scope import resolve_data_scope_dept_ids

        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return
        visible_dept_ids = await resolve_data_scope_dept_ids(self.db, session, IAM_DEPT_PAGE)
        if visible_dept_ids is None:
            return
        allowed_ids = set(visible_dept_ids)
        if any(dept_id not in allowed_ids for dept_id in unique_ids):
            raise AuthorizationError("Dept is outside current data scope")
