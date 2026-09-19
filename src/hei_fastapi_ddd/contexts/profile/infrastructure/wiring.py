"""profile 限界上下文依赖装配。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.auth.infrastructure.api.bind_code_adapter import get_bind_code_port
from hei_fastapi_ddd.contexts.iam.infrastructure.api.account_api_adapter import get_account_api
from hei_fastapi_ddd.contexts.iam.infrastructure.api.org_read_adapter import get_iam_org_read_api
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import (
    IamRelationRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.wiring import get_password_history_port
from hei_fastapi_ddd.contexts.profile.application.admin.admin_application_service import (
    ProfileUserAdminService,
)
from hei_fastapi_ddd.contexts.profile.application.identity.identity_application_service import (
    ProfileIdentityService,
    RealNameCaseService,
)
from hei_fastapi_ddd.contexts.profile.application.portal.portal_application_service import (
    ProfileUserPortalService,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.api.identity_provider_registry_adapter import (
    get_identity_provider_registry_port,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.admin_repository import (
    ProfileUserAdminRepositoryImpl,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.identity_repository import (
    ProfileIdentityRepositoryImpl,
    RealNameCaseRecordRepositoryImpl,
    RealNameCaseRepositoryImpl,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_repository import (
    ProfileUserPortalRepositoryImpl,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session


def build_profile_user_admin_service(db: AsyncSession) -> ProfileUserAdminService:
    # 延迟导入，打断 auth.wiring ↔ profile.wiring 循环
    from hei_fastapi_ddd.contexts.auth.infrastructure.wiring import get_account_session_service

    account_api = get_account_api(db)
    relation_repo = IamRelationRepositoryImpl(db)
    return ProfileUserAdminService(
        db,
        repo=ProfileUserAdminRepositoryImpl(db),
        account_api=account_api,
        org_read_api=get_iam_org_read_api(db),
        password_port=get_password_history_port(db),
        session_service=get_account_session_service(
            db, account_api=account_api, relation_repo=relation_repo
        ),
        bind_code_port=get_bind_code_port(db),
    )


def get_profile_user_admin_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProfileUserAdminService:
    return build_profile_user_admin_service(db)


def build_profile_user_portal_service(db: AsyncSession) -> ProfileUserPortalService:
    from hei_fastapi_ddd.contexts.auth.infrastructure.wiring import get_account_session_service

    account_api = get_account_api(db)
    relation_repo = IamRelationRepositoryImpl(db)
    return ProfileUserPortalService(
        db,
        repo=ProfileUserPortalRepositoryImpl(db),
        account_api=account_api,
        org_read_api=get_iam_org_read_api(db),
        password_port=get_password_history_port(db),
        session_service=get_account_session_service(
            db, account_api=account_api, relation_repo=relation_repo
        ),
        bind_code_port=get_bind_code_port(db),
    )


def get_profile_user_portal_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProfileUserPortalService:
    return build_profile_user_portal_service(db)


def build_profile_identity_service(db: AsyncSession) -> ProfileIdentityService:
    account_api = get_account_api(db)
    return ProfileIdentityService(
        db,
        identity_repo=ProfileIdentityRepositoryImpl(db),
        case_repo=RealNameCaseRepositoryImpl(db),
        account_api=account_api,
    )


def build_real_name_case_service(db: AsyncSession) -> RealNameCaseService:
    account_api = get_account_api(db)
    identity_repo = ProfileIdentityRepositoryImpl(db)
    case_repo = RealNameCaseRepositoryImpl(db)
    return RealNameCaseService(
        db,
        account_api=account_api,
        identity_repo=identity_repo,
        case_repo=case_repo,
        case_record_repo=RealNameCaseRecordRepositoryImpl(db),
        provider_registry=get_identity_provider_registry_port(),
    )


def get_profile_identity_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProfileIdentityService:
    return build_profile_identity_service(db)
