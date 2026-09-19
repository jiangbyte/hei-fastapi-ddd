"""Author: Charlie

账户应用服务：账户生命周期、密码策略、授权以及数据范围可见性校验。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.account.account_read_service import AccountReadService
from hei_fastapi_ddd.contexts.iam.application.account.dto import (
    AccountCreateCommand,
    AccountGrantClientResourceCommand,
    AccountGrantDeptCommand,
    AccountGrantGroupCommand,
    AccountGrantResourceCommand,
    AccountGrantRoleCommand,
    AccountPageQuery,
    AccountUpdateCommand,
    AccountUpdateLoginIdentityCommand,
    grant_items_to_dicts,
)
from hei_fastapi_ddd.contexts.iam.application.account.notify import notify_account_cancel_lifecycle
from hei_fastapi_ddd.contexts.iam.application.client.client_application_service import (
    ClientResourceService,
)
from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import (
    ResourceService,
)
from hei_fastapi_ddd.contexts.iam.application.support.audit_port import IamAuditPort
from hei_fastapi_ddd.contexts.iam.domain.account.aggregate import Account
from hei_fastapi_ddd.contexts.iam.domain.account.repository import AccountRepository
from hei_fastapi_ddd.contexts.iam.domain.enums import GrantSubjectType
from hei_fastapi_ddd.contexts.iam.domain.group.repository import GroupRepository
from hei_fastapi_ddd.contexts.iam.domain.relation.repository import IamRelationRepositoryPort
from hei_fastapi_ddd.contexts.iam.domain.role.repository import RoleRepository
from hei_fastapi_ddd.contexts.profile.application.api.profile_upsert_port import ProfileUpsertPort
from hei_fastapi_ddd.contexts.profile.application.identity.identity_application_service import (
    ProfileIdentityService,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.messaging import emit
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.data_scope import IAM_DEPT_PAGE, resolve_data_scope_dept_ids
from hei_fastapi_ddd.shared.security.password import hash_password_async
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.security.transport import decrypt_password
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import AuthorizationError, BusinessError


class AccountService:
    """账户应用服务，编排仓储与资料仓储完成账户及授权的读写。"""

    def __init__(
        self,
        db: AsyncSession,
        *,
        repo: AccountRepository,
        profile_port: ProfileUpsertPort,
        relation_repo: IamRelationRepositoryPort,
        audit: IamAuditPort,
        read_service: AccountReadService,
        resource_service: ResourceService,
        client_resource_service: ClientResourceService,
        role_repo: RoleRepository,
        group_repo: GroupRepository,
        identity_service: ProfileIdentityService,
    ):
        self.db = db
        self.audit = audit
        self.repo = repo
        self.profile_port = profile_port
        self.relation_repo = relation_repo
        self.read_service = read_service
        self.resource_service = resource_service
        self.client_resource_service = client_resource_service
        self.role_repo = role_repo
        self.group_repo = group_repo
        self.identity_service = identity_service

    async def create(self, command: AccountCreateCommand) -> None:
        """创建账户并同步写入对应端的用户资料。"""
        self._ensure_status_not_cancelled(command)
        password = await self._resolve_password(payload.password, payload.password_key_id)
        if not password:
            password = (settings.auth.default_password or "").strip()
        if not password:
            raise BusinessError("Password is required")
        async with transactional(self.db):
            account = await self.repo.create(
                command.model_dump(),
                password_hash=await hash_password_async(password),
            )
            match payload.account_type:
                case AccountType.ADMIN:
                    await self.profile_port.upsert_admin_profile(
                        self._profile_user_admin_payload(account["id"], command),
                    )
                case AccountType.PORTAL:
                    await self.profile_port.upsert_portal_profile(
                        self._profile_user_portal_payload(account["id"], command),
                    )
                case _:
                    raise BusinessError(f"Unsupported account type: {payload.account_type}")
        audit_snapshots.created_entity(account)

    async def update(
        self,
        command: AccountUpdateCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """更新账户与资料；传入 session 时先校验账户可见性。"""
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:update", [payload.id])
        self._ensure_status_not_cancelled(command)
        password = (
            await self._resolve_password(payload.password, payload.password_key_id)
            if payload.password
            else None
        )
        existing = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            password_hash = await hash_password_async(password) if password else None
            await self.repo.update(command.id, command.model_dump(), password_hash=password_hash)
            account = await self.repo.get_required(payload.id)
            match account["account_type"]:
                case AccountType.ADMIN.value:
                    await self.profile_port.upsert_admin_profile(
                        self._profile_user_admin_payload(payload.id, payload),
                    )
                case AccountType.PORTAL.value:
                    await self.profile_port.upsert_portal_profile(
                        self._profile_user_portal_payload(payload.id, payload),
                    )
                case _:
                    raise BusinessError(f"Unsupported account type: {account['account_type']}")
        updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)

    async def update_login_identity(
        self,
        command: AccountUpdateLoginIdentityCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """更新邮箱/手机号登录身份。"""
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:update", [payload.id])
        account = await self.repo.get_required(payload.id)
        if account["account_status"] == AccountStatusEnum.CANCELLED.value:
            raise BusinessError("已注销账号不允许通过管理端修改")
        if payload.email_login_enabled and not str(payload.email or "").strip():
            raise BusinessError("Email login requires an email")
        if payload.phone_login_enabled and not str(payload.phone or "").strip():
            raise BusinessError("Phone login requires a phone")
        audit_snapshots.before_entity(account)
        async with transactional(self.db):
            await self.repo.replace_secondary_login_identities(
                payload.id,
                email_login_enabled=bool(payload.email_login_enabled),
                email=payload.email,
                phone_login_enabled=bool(payload.phone_login_enabled),
                phone=payload.phone,
            )
        updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest, session: SessionPayload | None = None) -> None:
        """删除账户，并在事务外清理对应在线会话。"""
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:delete", payload.ids)
        accounts = await self.repo.list_accounts_by_ids(payload.ids)
        session_targets = [(account["account_type"], account["id"]) for account in accounts]
        audit_snapshots.deleted_all(accounts)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)
        # 1. 聚合登记删除事件；2. 通过集成事件通知 auth 清理会话（禁止直连 SessionService）
        for account in accounts:
            agg = Account(id=account["id"], account_type=account["account_type"], account_status=account.account_status)
            agg.mark_deleted()
            _ = agg.pull_domain_events()
        if session_targets:
            await emit("on_accounts_sessions_deleted", session_targets=session_targets)

    async def purge_expired_cancelled_accounts(
        self,
        retention_days: int | None = None,
    ) -> int:
        """彻底删除注销超过保留期的账户，并向快照联系方式发送通知。"""
        days = (
            retention_days
            if retention_days is not None
            else config_reader.get_int("ACCOUNT_CANCEL_RETENTION_DAYS", 15)
        )
        cutoff = datetime.now(UTC) - timedelta(days=days)
        account_ids = await self.repo.list_expired_cancelled_account_ids(cutoff)
        if not account_ids:
            return 0
        accounts = await self.repo.list_accounts_by_ids(account_ids)
        session_targets = [(account["account_type"], account["id"]) for account in accounts]
        notify_jobs = [
            (
                account.get("cancel_notify_email"),
                account.get("cancel_notify_phone"),
            )
            for account in accounts
        ]
        async with transactional(self.db):
            await self.repo.purge_many(account_ids)
        if session_targets:
            await emit("on_accounts_sessions_deleted", session_targets=session_targets)
        purged_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        variables = {
            "app_name": settings.app.name,
            "purged_at": purged_at,
            "retention_days": str(days),
        }
        for email, phone in notify_jobs:
            await notify_account_cancel_lifecycle(
                scene="ACCOUNT_PURGED",
                email=email,
                phone=phone,
                variables=variables,
            )
        return len(account_ids)

    async def detail(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """查询账户详情，传入 session 时先校验可见性。"""
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:detail", [query.id])
        accounts = [await self.repo.get_required(query.id)]
        item = (await self.read_service.build_account_views(accounts, full=True))[0]
        identity_status = await self.identity_service.get_status_for_account(query.id)
        item.identity_status = identity_status
        if identity_status.real_name_masked:
            item.name = identity_status.real_name_masked
        return item

    async def page_admin(
        self,
        query: AccountPageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[dict]:
        """分页查询账户，叠加当前会话的数据范围过滤。"""
        accounts, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
            session=session,
        )
        items = await self.read_service.build_account_views(accounts, full=False)
        return build_page(query, total, items)

    async def own_resource(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回账户拥有的资源授权（模块树 + 授权明细）。"""
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:ownresource", [query.id])
        account = await self.repo.get_required(query.id)
        account_type = AccountType(account["account_type"])
        return dict(
            id=query.id,
            modules=await self.resource_service.list_grant_modules(
                module_client=account_type,
            ),
            grant_info_list=[
                dict(grant)
                for grant in await self.relation_repo.list_subject_resource_grants(
                    GrantSubjectType.ACCOUNT,
                    query.id,
                    account_type=account["account_type"],
                )
            ],
        )

    async def grant_resource(
        self,
        command: AccountGrantResourceCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户资源授权，并刷新账户会话。"""
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:grantresource", [payload.id])
        account = await self.repo.get_required(payload.id)
        subject = await self._audit_subject(payload.id)
        audit_snapshots.subject(subject or payload.id)
        audit_snapshots.resource_id(payload.id)
        old_grants = await self.relation_repo.list_subject_resource_grants(
            GrantSubjectType.ACCOUNT,
            payload.id,
            account_type=account["account_type"],
        )
        audit_snapshots.before(await self.audit.grant_resource_field("资源", old_grants))
        async with transactional(self.db):
            await self.relation_repo.replace_subject_resource_grant_infos(
                GrantSubjectType.ACCOUNT,
                payload.id,
                payload.grant_info_list,
                account_type=account["account_type"],
            )
        new_grants = await self.relation_repo.list_subject_resource_grants(
            GrantSubjectType.ACCOUNT,
            payload.id,
            account_type=account["account_type"],
        )
        audit_snapshots.after(await self.audit.grant_resource_field("资源", new_grants))
        await self._refresh_accounts([payload.id])

    async def own_client_resource(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回账户拥有的客户端资源授权。"""
        if session is not None:
            await self._ensure_accounts_visible(
                session, "iam:account:ownclientresource", [query.id]
            )
        account = await self.repo.get_required(query.id)
        account_type = AccountType(account["account_type"])
        return dict(
            id=query.id,
            modules=await Clientself.resource_service.list_grant_modules(account_type),
            grant_info_list=[
                dict(grant)
                for grant in await self.relation_repo.list_subject_client_resource_grants(
                    GrantSubjectType.ACCOUNT,
                    query.id,
                    account_type=account["account_type"],
                )
            ],
        )

    async def grant_client_resource(
        self,
        command: AccountGrantClientResourceCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户客户端资源授权，并刷新账户会话。"""
        if session is not None:
            await self._ensure_accounts_visible(
                session, "iam:account:grantclientresource", [payload.id]
            )
        account = await self.repo.get_required(payload.id)
        subject = await self._audit_subject(payload.id)
        audit_snapshots.subject(subject or payload.id)
        audit_snapshots.resource_id(payload.id)
        old_grants = await self.relation_repo.list_subject_client_resource_grants(
            GrantSubjectType.ACCOUNT,
            payload.id,
            account_type=account["account_type"],
        )
        audit_snapshots.before(
            await self.audit.grant_client_resource_field("客户端资源", old_grants)
        )
        async with transactional(self.db):
            await self.relation_repo.replace_subject_client_resource_grant_infos(
                GrantSubjectType.ACCOUNT,
                payload.id,
                payload.grant_info_list,
                account_type=account["account_type"],
            )
        new_grants = await self.relation_repo.list_subject_client_resource_grants(
            GrantSubjectType.ACCOUNT,
            payload.id,
            account_type=account["account_type"],
        )
        audit_snapshots.after(
            await self.audit.grant_client_resource_field("客户端资源", new_grants)
        )
        await self._refresh_accounts([payload.id])

    async def own_role(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回账户直接绑定的角色（叠加角色数据范围过滤）。"""
        role_filter = (
            await self._role_scope_filter(session, "iam:account:ownrole")
            if session is not None
            else None
        )
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:ownrole", [query.id])
        role_ids = await self.repo.list_account_direct_role_ids(query.id, role_filter)
        return dict(
            id=query.id,
            roles=await self.repo.list_roles_by_ids(role_ids),
            role_ids=role_ids,
        )

    async def grant_role(
        self,
        command: AccountGrantRoleCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户角色，并刷新账户会话。"""
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:grantrole", [payload.id])
            await self._ensure_roles_visible(session, "iam:account:grantrole", payload.role_ids)
        subject = await self._audit_subject(payload.id)
        audit_snapshots.subject(subject or payload.id)
        audit_snapshots.resource_id(payload.id)
        old_role_ids = await self.repo.list_account_direct_role_ids(payload.id)
        audit_snapshots.before(await self.audit.role_ids_field(old_role_ids))
        async with transactional(self.db):
            await self.repo.replace_account_roles(payload)
        audit_snapshots.after(await self.audit.role_ids_field(payload.role_ids))
        await self._refresh_accounts([payload.id])

    async def own_group(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回账户直接绑定的账户组（叠加组数据范围过滤）。"""
        group_filter = (
            await self._group_scope_filter(session, "iam:account:owngroup")
            if session is not None
            else None
        )
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:owngroup", [query.id])
        group_ids = await self.repo.list_account_direct_group_ids(query.id, group_filter)
        return dict(
            id=query.id,
            groups=await self.repo.list_groups_by_ids(group_ids),
            group_ids=group_ids,
        )

    async def grant_group(
        self,
        command: AccountGrantGroupCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户账户组，并刷新账户会话。"""
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:grantgroup", [payload.id])
            await self._ensure_groups_visible(session, "iam:account:grantgroup", payload.group_ids)
        subject = await self._audit_subject(payload.id)
        audit_snapshots.subject(subject or payload.id)
        audit_snapshots.resource_id(payload.id)
        old_group_ids = await self.repo.list_account_direct_group_ids(payload.id)
        audit_snapshots.before(await self.audit.group_ids_field(old_group_ids))
        async with transactional(self.db):
            await self.repo.replace_account_groups(payload)
        audit_snapshots.after(await self.audit.group_ids_field(payload.group_ids))
        await self._refresh_accounts([payload.id])

    async def own_dept(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """返回账户的部门授权（仅返回当前可见部门）。"""
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:owndept", [query.id])
        visible_dept_ids = (
            await resolve_data_scope_dept_ids(self.db, session, "iam:account:owndept")
            if session is not None
            else None
        )
        return dict(
            id=query.id,
            grant_info_list=await self.repo.list_account_dept_grants(query.id, visible_dept_ids),
        )

    async def grant_dept(
        self,
        command: AccountGrantDeptCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """全量替换账户部门，并刷新账户会话。"""
        if session is not None:
            await self._ensure_accounts_visible(session, "iam:account:grantdept", [payload.id])
            await self._ensure_depts_visible(
                session,
                "iam:account:grantdept",
                [item.dept_id for item in payload.grant_info_list],
            )
        subject = await self._audit_subject(payload.id)
        audit_snapshots.subject(subject or payload.id)
        audit_snapshots.resource_id(payload.id)
        old_grants = await self.repo.list_account_dept_grants(payload.id)
        audit_snapshots.before(await self.audit.dept_grant_field(old_grants))
        async with transactional(self.db):
            await self.repo.replace_account_depts(payload)
        audit_snapshots.after(await self.audit.dept_grant_field(payload.grant_info_list))
        await self._refresh_accounts([payload.id])

    async def _refresh_accounts(self, account_ids: list[str]) -> None:
        """刷新指定账户的在线会话缓存。"""
        # 1. 聚合登记授权变更事件
        for account_id in sorted(set(account_ids)):
            agg = Account(id=account_id, account_type="", account_status="")
            agg.mark_authorization_changed("grant")
            _ = agg.pull_domain_events()
        # 2. 集成事件通知 auth 刷新会话投影
        await emit("on_authorization_changed", account_ids=sorted(set(account_ids)))

    async def _account_scope_filter(self, session: SessionPayload, permission_key: str):
        """构造账户数据范围过滤条件。"""
        return await build_data_scope_filter(
            self.db,
            session,
            permission_key,
            owner_column=SysAccount.id,
            dept_column=SysIamRelation.target_id,
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

    async def _group_scope_filter(self, session: SessionPayload, permission_key: str):
        """构造账户组数据范围过滤条件。"""
        return await build_data_scope_filter(
            self.db,
            session,
            permission_key,
            owner_column=SysGroup.created_by,
            dept_column=SysGroup.owner_dept_id,
        )

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
        count = await self.repo.count_accounts_in_scope(
            unique_ids,
            session=session,
            permission=IAM_ACCOUNT_PAGE,
        )
        if count != len(unique_ids):
            raise AuthorizationError("Account is outside current data scope")

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
        count = await self.role_repo.count_roles_in_scope(
            unique_ids,
            session=session,
            permission=IAM_ROLE_PAGE,
        )
        if count != len(unique_ids):
            raise AuthorizationError("Role is outside current data scope")

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
        count = await self.group_repo.count_groups_in_scope(
            unique_ids,
            session=session,
            permission=IAM_GROUP_PAGE,
        )
        if count != len(unique_ids):
            raise AuthorizationError("Group is outside current data scope")

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
        if any(dept_id not in set(visible_dept_ids) for dept_id in unique_ids):
            raise AuthorizationError("Dept is outside current data scope")

    def _profile_user_admin_payload(
        self,
        account_id: str,
        payload: AccountCreateCommand | AccountUpdateCommand,
    ) -> dict:
        """从账户请求构造管理端用户资料写入字典。"""
        return {
            "account_id": account_id,
            "nickname": payload.nickname,
            "avatar": payload.avatar,
            "signature": payload.signature,
            "phone": payload.phone,
            "email": payload.email,
            "remark": payload.remark,
        }

    def _profile_user_portal_payload(
        self,
        account_id: str,
        payload: AccountCreateCommand | AccountUpdateCommand,
    ) -> dict:
        """从账户请求构造门户端用户资料写入字典。"""
        return {
            "account_id": account_id,
            "nickname": payload.nickname,
            "avatar": payload.avatar,
            "signature": payload.signature,
            "phone": payload.phone,
            "email": payload.email,
        }

    def _ensure_status_not_cancelled(
        self,
        payload: AccountCreateCommand | AccountUpdateCommand,
    ) -> None:
        """禁止通过管理端将账户状态直接设为已注销（对齐领域规则）。"""
        # 1. 管理端不得直接写入注销态
        if payload.account_status == AccountStatusEnum.CANCELLED:
            raise BusinessError("注销状态不允许通过管理端设置")

    def _ensure_login_contact_payload(
        self,
        payload: AccountCreateCommand | AccountUpdateCommand,
    ) -> None:
        """启用邮箱/手机号登录时校验对应联系方式非空。"""
        if (
            payload.email_login_enabled
            and not str(payload.email_identity or payload.email or "").strip()
        ):
            raise BusinessError("Email login requires an email")
        if (
            payload.phone_login_enabled
            and not str(payload.phone_identity or payload.phone or "").strip()
        ):
            raise BusinessError("Phone login requires a phone")

    async def _resolve_password(self, password: str, password_key_id: str | None) -> str:
        """按传输密钥解密密码，无密钥时原样返回。"""
        if not password_key_id:
            return password
        return await decrypt_password(password_key_id, password)
