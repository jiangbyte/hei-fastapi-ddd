""" Author: Charlie """

from hei_fastapi_ddd.contexts.iam.api.account_schemas import AccountCreateRequest
from hei_fastapi_ddd.contexts.iam.application.account.account_application_service import (
    AccountService,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import (
    AccountRepository,
)
from hei_fastapi_ddd.contexts.profile.application.admin.admin_application_service import (
    ProfileUserAdminService,
)
from hei_fastapi_ddd.shared.config.enums import AccountType


async def test_create_admin_account_creates_profile(db_session):
    await AccountService(db_session).create(
        AccountCreateRequest(
            account="admin2",
            password="Admin@123456",
            account_type=AccountType.ADMIN,
            name="Admin 2",
            nickname="Admin 2",
            avatar=None,
            signature=None,
            phone=None,
            email=None,
        )
    )
    await db_session.commit()
    account = await AccountRepository(db_session).get_account_by_account("admin2")
    assert account is not None
    assert account.id is not None
    profile = await ProfileUserAdminService(db_session).get_profile(account.id)
    assert profile is not None
