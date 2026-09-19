"""Author: Charlie

账户组应用服务：依赖 domain 仓储端口，不依赖 infrastructure / api。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.client.client_application_service import (
    ClientResourceService,
)
from hei_fastapi_ddd.contexts.iam.application.group.dto import (
    GroupCreateCommand,
    GroupGrantClientResourceCommand,
    GroupGrantResourceCommand,
    GroupGrantRoleCommand,
    GroupGrantUserCommand,
    GroupOwnClientResourceQuery,
    GroupOwnResourceQuery,
    GroupOwnRoleQuery,
    GroupPageQuery,
    GroupUpdateCommand,
)
from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import (
    ResourceService,
)
from hei_fastapi_ddd.contexts.iam.application.support.audit_port import IamAuditPort
from hei_fastapi_ddd.contexts.iam.domain.account.repository import AccountRepository
from hei_fastapi_ddd.contexts.iam.domain.enums import GrantSubjectType
from hei_fastapi_ddd.contexts.iam.domain.group.repository import GroupRepository
from hei_fastapi_ddd.contexts.iam.domain.relation.repository import IamRelationRepositoryPort
from hei_fastapi_ddd.contexts.iam.domain.role.repository import RoleRepository
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.messaging import emit
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.data_scope import (
    IAM_ACCOUNT_PAGE,
    IAM_DEPT_PAGE,
    IAM_GROUP_PAGE,
    IAM_ROLE_PAGE,
    resolve_data_scope_dept_ids,
)
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import AuthorizationError


class GroupService:
    """账户组应用服务。"""

    def __init__(
        self,
        db: AsyncSession,
        audit: IamAuditPort,
        *,
        repo: GroupRepository,
        relation_repo: IamRelationRepositoryPort,
        resource_service: ResourceService,
        client_resource_service: ClientResourceService,
        account_repo: AccountRepository,
        role_repo: RoleRepository,
    ):
        self.db = db
        self.audit = audit
        self.repo = repo
        self.relation_repo = relation_repo
        self.resource_service = resource_service
        self.client_resource_service = client_resource_service
        self.account_repo = account_repo
        self.role_repo = role_repo

    async def create(
        self,
        command: GroupCreateCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """创建账户组，传入 session 时校验所属部门可见性。"""
        if session is not None and command.owner_dept_id:
            await self._ensure_depts_visible(session, "iam:group:create", [command.owner_dept_id])
        async with transactional(self.db):
            entity = await self.repo.create(command.model_dump())
        audit_snapshots.created_entity(entity)

    async def update(
        self,
        command: GroupUpdateCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """更新账户组，传入 session 时校验可见性。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:update", [command.id])
            if command.owner_dept_id:
                await self._ensure_depts_visible(
                    session,
                    "iam:group:update",
                    [command.owner_dept_id],
                )
        existing = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(command.model_dump())
        updated = await self.repo.get_required(command.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest, session: SessionPayload | None = None) -> None:
        """删除账户组，传入 session 时先校验可见性。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:delete", payload.ids)
        entities = await self.repo.list_by_ids(payload.ids)
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(self, query: IdQuery, session: SessionPayload | None = None) -> dict:
        """查询账户组详情。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:detail", [query.id])
        return await self.repo.get_required(query.id)

    async def page_admin(
        self,
        query: GroupPageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[dict]:
        """分页查询账户组，叠加数据范围过滤。"""
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
            session=session,
        )
        return build_page(query, total, items)  # type: ignore[arg-type]

    async def own_user(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回账户组成员（含全部可见账户与已选成员）。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:ownuser", [query.id])
        users = await self.repo.list_accounts(session=session)
        group_users = await self.repo.list_group_accounts(query.id, session=session)
        return {
            "id": query.id,
            "users": users,
            "account_ids": [account["id"] for account in group_users],
        }

    async def grant_user(
        self,
        command: GroupGrantUserCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户组成员，并刷新受影响账户会话。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:grantuser", [command.id])
            await self._ensure_accounts_visible(session, "iam:group:grantuser", command.account_ids)
        group = await self.repo.get_required(command.id)
        audit_snapshots.subject(group["name"])
        audit_snapshots.resource_id(group["id"])
        old_account_ids = await self.repo.list_account_ids_by_group(command.id)
        audit_snapshots.before(await self.audit.account_ids_field(old_account_ids))
        async with transactional(self.db):
            await self.repo.replace_group_accounts(command.model_dump())
        audit_snapshots.after(await self.audit.account_ids_field(command.account_ids))
        await self._refresh_accounts(sorted(set(old_account_ids + command.account_ids)))

    async def own_role(
        self,
        query: GroupOwnRoleQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回账户组绑定的角色。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:ownrole", [query.id])
        account_type = query.account_type.value if query.account_type else None
        role_ids = await self.repo.list_group_role_ids(
            query.id,
            session=session,
            account_type=account_type,
        )
        return {
            "id": query.id,
            "roles": await self.repo.list_roles_by_ids(role_ids),
            "role_ids": role_ids,
        }

    async def grant_role(
        self,
        command: GroupGrantRoleCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户组角色，并刷新成员账户会话。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:grantrole", [command.id])
            await self._ensure_roles_visible(session, "iam:group:grantrole", command.role_ids)
        group = await self.repo.get_required(command.id)
        audit_snapshots.subject(group["name"])
        audit_snapshots.resource_id(group["id"])
        account_type = command.account_type.value
        old_role_ids = await self.repo.list_group_role_ids(command.id, account_type=account_type)
        audit_snapshots.before(await self.audit.role_ids_field(old_role_ids))
        async with transactional(self.db):
            account_ids = await self.repo.list_account_ids_by_group(command.id)
            await self.repo.replace_group_roles(command.model_dump())
        audit_snapshots.after(await self.audit.role_ids_field(command.role_ids))
        await self._refresh_accounts(account_ids)

    async def own_resource(
        self,
        query: GroupOwnResourceQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回账户组拥有的资源授权。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:ownresource", [query.id])
        return {
            "id": query.id,
            "modules": await self.resource_service.list_grant_modules(
                module_client=query.account_type,
            ),
            "grant_info_list": await self.relation_repo.list_subject_resource_grants(
                GrantSubjectType.GROUP,
                query.id,
                account_type=query.account_type,
            ),
        }

    async def grant_resource(
        self,
        command: GroupGrantResourceCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户组资源授权，并刷新成员账户会话。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:grantresource", [command.id])
        group = await self.repo.get_required(command.id)
        audit_snapshots.subject(group["name"])
        audit_snapshots.resource_id(group["id"])
        old_grants = await self.relation_repo.list_subject_resource_grants(
            GrantSubjectType.GROUP,
            command.id,
            account_type=command.account_type,
        )
        audit_snapshots.before(await self.audit.grant_resource_field("资源", old_grants))
        async with transactional(self.db):
            account_ids = await self.repo.list_account_ids_by_group(command.id)
            await self.relation_repo.replace_subject_resource_grant_infos(
                GrantSubjectType.GROUP,
                command.id,
                command.grant_info_list,
                account_type=command.account_type,
            )
        new_grants = await self.relation_repo.list_subject_resource_grants(
            GrantSubjectType.GROUP,
            command.id,
            account_type=command.account_type,
        )
        audit_snapshots.after(await self.audit.grant_resource_field("资源", new_grants))
        await self._refresh_accounts(account_ids)

    async def own_client_resource(
        self,
        query: GroupOwnClientResourceQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回账户组拥有的客户端资源授权。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:ownclientresource", [query.id])
        return {
            "id": query.id,
            "modules": await self.client_resource_service.list_grant_modules(query.account_type),
            "grant_info_list": await self.relation_repo.list_subject_client_resource_grants(
                GrantSubjectType.GROUP,
                query.id,
                account_type=query.account_type,
            ),
        }

    async def grant_client_resource(
        self,
        command: GroupGrantClientResourceCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户组客户端资源授权，并刷新成员账户会话。"""
        if session is not None:
            await self._ensure_groups_visible(session, "iam:group:grantclientresource", [command.id])
        group = await self.repo.get_required(command.id)
        audit_snapshots.subject(group["name"])
        audit_snapshots.resource_id(group["id"])
        old_grants = await self.relation_repo.list_subject_client_resource_grants(
            GrantSubjectType.GROUP,
            command.id,
            account_type=command.account_type,
        )
        audit_snapshots.before(
            await self.audit.grant_client_resource_field("客户端资源", old_grants)
        )
        async with transactional(self.db):
            account_ids = await self.repo.list_account_ids_by_group(command.id)
            await self.relation_repo.replace_subject_client_resource_grant_infos(
                GrantSubjectType.GROUP,
                command.id,
                command.grant_info_list,
                account_type=command.account_type,
            )
        new_grants = await self.relation_repo.list_subject_client_resource_grants(
            GrantSubjectType.GROUP,
            command.id,
            account_type=command.account_type,
        )
        audit_snapshots.after(
            await self.audit.grant_client_resource_field("客户端资源", new_grants)
        )
        await self._refresh_accounts(account_ids)

    async def _refresh_accounts(self, account_ids: list[str]) -> None:
        await emit("on_authorization_changed", account_ids=sorted(set(account_ids)))

    async def _ensure_groups_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        group_ids: list[str],
    ) -> None:
        unique_ids = list(dict.fromkeys(group_ids))
        if not unique_ids:
            return
        count = await self.repo.count_groups_in_scope(
            unique_ids,
            session=session,
            permission=permission_key or IAM_GROUP_PAGE,
        )
        if count != len(unique_ids):
            raise AuthorizationError("Group is outside current data scope")

    async def _ensure_roles_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        role_ids: list[str],
    ) -> None:
        unique_ids = list(dict.fromkeys(role_ids))
        if not unique_ids:
            return
        count = await self.role_repo.count_roles_in_scope(
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
