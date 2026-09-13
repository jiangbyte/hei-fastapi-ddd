""" Author: Charlie """

from sqlalchemy import select

from hei_fastapi_ddd.contexts.iam.application.group.group_application_service import GroupService
from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import (
    ResourceService,
)
from hei_fastapi_ddd.contexts.iam.application.role.role_application_service import RoleService
from hei_fastapi_ddd.contexts.iam.domain.enums import (
    IamRelationTargetType,
    IamRelationType,
    ResourceType,
    RoleScopeType,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.group_po import SysGroup
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_po import SysIamRelation
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po import SysRole
from hei_fastapi_ddd.contexts.iam.interfaces.http.account_schemas import AccountRoleAssignRequest
from hei_fastapi_ddd.contexts.iam.interfaces.http.group_schemas import (
    GroupCreateRequest,
    GroupRoleAssignRequest,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.resource_schemas import (
    ResourceCreateRequest,
    ResourcePermissionBindRequest,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.role_schemas import (
    RoleCreateRequest,
    RoleGrantResourceRequest,
    RoleResourceGrantInfo,
)
from hei_fastapi_ddd.shared.config.enums import (
    AccountStatusEnum,
    AccountType,
)


async def _create_role(db_session, payload: RoleCreateRequest) -> str:
    await RoleService(db_session).create(payload)
    stmt = select(SysRole.id).where(SysRole.code == payload.code)
    role_id = (await db_session.execute(stmt)).scalar_one()
    await db_session.commit()
    return role_id


async def _create_resource(db_session, payload: ResourceCreateRequest) -> str:
    await ResourceService(db_session).create(payload)
    stmt = select(SysResource.id).where(SysResource.code == payload.code)
    resource_id = (await db_session.execute(stmt)).scalar_one()
    await db_session.commit()
    return resource_id


async def _create_group(db_session, payload: GroupCreateRequest) -> str:
    await GroupService(db_session).create(payload)
    stmt = select(SysGroup.id).where(SysGroup.name == payload.name)
    group_id = (await db_session.execute(stmt)).scalar_one()
    await db_session.commit()
    return group_id


async def test_assign_account_role_success(db_session):
    role_id = await _create_role(
        db_session,
        RoleCreateRequest(
            code="r1",
            name="Role1",
            category="SYSTEM",
            scope_type=RoleScopeType.PLATFORM.value,
        ),
    )
    account = SysAccount(
        password_hash="x",
        account_type=AccountType.ADMIN.value,
        account_status=AccountStatusEnum.ENABLED.value,
    )
    db_session.add(account)
    await db_session.flush()
    await db_session.commit()
    from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import (
        AccountRepository,
    )

    relation = await AccountRepository(db_session).assign_account_to_role(
        AccountRoleAssignRequest(account_id=account.id, role_id=role_id)
    )
    await db_session.commit()
    assert relation.account_id == account.id
    assert relation.role_id == role_id


async def test_bind_resource_permission_success(db_session, monkeypatch):
    async def fake_ensure_registered_permission_key(permission_key: str) -> None:
        assert permission_key == "iam:account:create"

    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service.ensure_registered_permission_key",
        fake_ensure_registered_permission_key,
    )

    resource_id = await _create_resource(
        db_session,
        ResourceCreateRequest(
            code="iam:button:create",
            name="Create Button",
            resource_type=ResourceType.BUTTON.value,
        ),
    )
    relation = await ResourceService(db_session).bind_resource_permission(
        ResourcePermissionBindRequest(resource_id=resource_id, permission_key="iam:account:create")
    )
    await db_session.commit()
    assert relation.resource_id == resource_id
    assert relation.permission_key == "iam:account:create"


async def test_assign_group_role_success(db_session):
    group_id = await _create_group(
        db_session, GroupCreateRequest(name="Group1", description="Test group")
    )
    role_id = await _create_role(
        db_session,
        RoleCreateRequest(
            code="r3",
            name="Role3",
            category="SYSTEM",
            scope_type=RoleScopeType.PLATFORM.value,
        ),
    )
    from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.group_repository import (
        GroupRepository,
    )

    relation = await GroupRepository(db_session).assign_group_to_role(
        GroupRoleAssignRequest(
            group_id=group_id,
            role_id=role_id,
            account_type=AccountType.ADMIN,
        )
    )
    await db_session.commit()
    assert relation.group_id == group_id
    assert relation.role_id == role_id


async def test_grant_role_resource_success(db_session):
    role_id = await _create_role(
        db_session,
        RoleCreateRequest(
            code="r4",
            name="Role4",
            category="SYSTEM",
            scope_type=RoleScopeType.PLATFORM.value,
        ),
    )
    resource_id = await _create_resource(
        db_session,
        ResourceCreateRequest(
            code="iam:resource:grant",
            name="Grant Resource",
            resource_type=ResourceType.BUTTON.value,
        ),
    )
    await RoleService(db_session).grant_resource(
        RoleGrantResourceRequest(
            id=role_id,
            account_type=AccountType.ADMIN,
            grant_info_list=[RoleResourceGrantInfo(resource_id=resource_id, permission_keys=[])],
        )
    )
    await db_session.commit()
    relation = (
        await db_session.execute(
            select(SysIamRelation).where(
                SysIamRelation.subject_id == role_id,
                SysIamRelation.relation_type == IamRelationType.SUBJECT_RESOURCE_GRANT.value,
                SysIamRelation.target_type == IamRelationTargetType.RESOURCE.value,
                SysIamRelation.target_id == resource_id,
            )
        )
    ).scalar_one()
    assert relation.subject_id == role_id
    assert relation.resource_id == resource_id
