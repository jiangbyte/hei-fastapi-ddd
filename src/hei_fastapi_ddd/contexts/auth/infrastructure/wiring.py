"""auth 限界上下文依赖装配。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.auth.application.auth_application_service import AuthService
from hei_fastapi_ddd.contexts.auth.application.oauth.oauth_application_service import (
    AuthOauthService,
)
from hei_fastapi_ddd.contexts.auth.application.session_admin_service import SessionAdminService
from hei_fastapi_ddd.contexts.auth.application.session_service import AccountSessionService
from hei_fastapi_ddd.contexts.auth.infrastructure.api.oauth_adapters import (
    get_oauth_binding_repository_port,
    get_oauth_client_port,
    get_oauth_exchange_store_port,
    get_oauth_state_store_port,
)
from hei_fastapi_ddd.contexts.iam.application.api.account_api import AccountApi
from hei_fastapi_ddd.contexts.iam.domain.account.password_port import AccountPasswordPort
from hei_fastapi_ddd.contexts.iam.domain.relation.repository import IamRelationRepositoryPort
from hei_fastapi_ddd.contexts.iam.infrastructure.api.account_api_adapter import get_account_api
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import (
    IamRelationRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.wiring import get_password_history_port
from hei_fastapi_ddd.contexts.profile.application.api.profile_upsert_port import ProfileUpsertPort
from hei_fastapi_ddd.contexts.profile.infrastructure.api.profile_read_adapter import (
    get_profile_read_port,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.api.profile_upsert_adapter import (
    get_profile_upsert_port,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session


def get_account_session_service(
    db: AsyncSession,
    *,
    account_api: AccountApi | None = None,
    relation_repo: IamRelationRepositoryPort | None = None,
) -> AccountSessionService:
    return AccountSessionService(
        db,
        account_api=account_api or get_account_api(db),
        relation_repo=relation_repo or IamRelationRepositoryImpl(db),
    )


def build_auth_service(db: AsyncSession) -> AuthService:
    account_api = get_account_api(db)
    relation_repo = IamRelationRepositoryImpl(db)
    return AuthService(
        db,
        account_api=account_api,
        relation_repo=relation_repo,
        session_service=get_account_session_service(
            db, account_api=account_api, relation_repo=relation_repo
        ),
        profile_port=get_profile_upsert_port(db),
        password_port=get_password_history_port(db),
        profile_read_port=get_profile_read_port(db),
    )


def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    return build_auth_service(db)


def get_auth_oauth_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthOauthService:
    auth = build_auth_service(db)
    return AuthOauthService(
        db,
        auth_service=auth,
        oauth_client=get_oauth_client_port(),
        state_store=get_oauth_state_store_port(),
        exchange_store=get_oauth_exchange_store_port(),
        binding_repo=get_oauth_binding_repository_port(db),
    )


def get_session_admin_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SessionAdminService:
    return SessionAdminService(db, account_api=get_account_api(db))

