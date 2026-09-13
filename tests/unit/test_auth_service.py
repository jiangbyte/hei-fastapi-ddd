""" Author: Charlie """

import pytest

from hei_fastapi_ddd.shared.config.enums import (
    AccountStatusEnum,
    AccountType,
)
from hei_fastapi_ddd.shared.exceptions.business import AuthenticationError
from hei_fastapi_ddd.shared.security.password import hash_password
from hei_fastapi_ddd.contexts.auth.interfaces.http.auth_schemas import LoginPayload
from hei_fastapi_ddd.contexts.auth.application.auth_application_service import AuthService
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount, SysAccountIdentity
from hei_fastapi_ddd.contexts.iam.domain.enums import (
    AccountIdentityType,
    GrantSubjectType,
    ResourceType,
    RoleScopeType,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource
from hei_fastapi_ddd.contexts.iam.domain.role.constants import SUPER_ADMIN_ROLE_CODE
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po import SysRole
from tests.iam_relation_helpers import (
    account_role,
    resource_permission,
    subject_resource_grant,
)


async def _seed_account(
    db_session,
    *,
    identifier: str,
    password: str,
    account_type: AccountType,
) -> SysAccount:
    account = SysAccount(
        password_hash=hash_password(password),
        account_type=account_type.value,
        account_status=AccountStatusEnum.ENABLED.value,
    )
    db_session.add(account)
    await db_session.flush()
    db_session.add(
        SysAccountIdentity(
            account_id=account.id,
            identity_type=AccountIdentityType.ACCOUNT.value,
            identifier=identifier,
            verified=True,
            is_primary=True,
        )
    )
    return account


async def test_admin_login_success(db_session):
    account = await _seed_account(
        db_session,
        identifier="admin",
        password="Admin@123456",
        account_type=AccountType.ADMIN,
    )

    role = SysRole(
        code=SUPER_ADMIN_ROLE_CODE,
        name="Super Admin",
        category="SYSTEM",
        scope_type=RoleScopeType.PLATFORM.value,
    )
    resource = SysResource(
        code="iam:user:list",
        name="Account List Resource",
        resource_type=ResourceType.BUTTON.value,
    )
    db_session.add_all([role, resource])
    await db_session.flush()
    db_session.add(resource_permission(resource.id, "iam:account:list"))
    db_session.add(subject_resource_grant(GrantSubjectType.ROLE, role.id, resource.id))
    db_session.add(account_role(account.id, role.id))
    await db_session.commit()

    payload = await AuthService(db_session).login(
        LoginPayload(account="admin", password="Admin@123456", account_type=AccountType.ADMIN)
    )
    assert payload.account_id == account.id
    assert payload.account_type == AccountType.ADMIN.value
    assert "iam:account:list" in payload.permission_keys
    assert "*:*:*" in payload.permission_keys


async def test_portal_account_cannot_login_admin_account_type(db_session):
    await _seed_account(
        db_session,
        identifier="portal_account",
        password="Portal@123456",
        account_type=AccountType.PORTAL,
    )
    await db_session.commit()

    with pytest.raises(AuthenticationError):
        await AuthService(db_session).login(
            LoginPayload(
                account="portal_account",
                password="Portal@123456",
                account_type=AccountType.ADMIN,
            )
        )
