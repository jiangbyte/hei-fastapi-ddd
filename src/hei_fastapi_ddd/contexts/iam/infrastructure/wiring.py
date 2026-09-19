"""IAM 限界上下文依赖装配。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.account.account_application_service import (
    AccountService,
)
from hei_fastapi_ddd.contexts.iam.application.account.account_read_service import AccountReadService
from hei_fastapi_ddd.contexts.iam.application.client.client_application_service import (
    ClientModuleService,
    ClientResourceService,
)
from hei_fastapi_ddd.contexts.iam.application.dept.dept_application_service import DeptService
from hei_fastapi_ddd.contexts.iam.application.group.group_application_service import GroupService
from hei_fastapi_ddd.contexts.iam.application.position.position_application_service import (
    PositionService,
)
from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import (
    ResourceModuleService,
    ResourceService,
)
from hei_fastapi_ddd.contexts.iam.application.role.role_application_service import RoleService
from hei_fastapi_ddd.contexts.profile.infrastructure.api.profile_read_adapter import (
    get_profile_read_port,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.api.account_api_adapter import get_account_api
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import (
    AccountRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.client_repository import (
    ClientModuleRepository,
    ClientResourceRepository,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.dept_repository import (
    DeptRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.group_repository import (
    GroupRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.password_history_repository import (
    PasswordHistoryRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.position_repository import (
    PositionRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import (
    IamRelationRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_repository import (
    ResourceModuleRepository,
    ResourceRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_repository import (
    RoleRepositoryImpl,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.support.iam_audit_adapter import IamAuditAdapter
from hei_fastapi_ddd.contexts.profile.infrastructure.api.profile_read_adapter import (
    ProfileReadAdapter,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.api.profile_upsert_adapter import (
    ProfileUpsertAdapter,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session

__all__ = ["get_account_api"]


def _audit(db: AsyncSession) -> IamAuditAdapter:
    return IamAuditAdapter(db)


def _relation(db: AsyncSession) -> IamRelationRepositoryImpl:
    return IamRelationRepositoryImpl(db)


def _account_repo(db: AsyncSession) -> AccountRepositoryImpl:
    return AccountRepositoryImpl(db)


def get_position_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> PositionService:
    return PositionService(db, PositionRepositoryImpl(db))


def get_dept_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeptService:
    return DeptService(db, DeptRepositoryImpl(db))


def get_resource_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceService:
    return ResourceService(
        db,
        _audit(db),
        repo=ResourceRepositoryImpl(db),
        relation_repo=_relation(db),
    )


def get_resource_module_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceModuleService:
    return ResourceModuleService(db, ResourceModuleRepository(db))


def get_client_resource_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClientResourceService:
    return ClientResourceService(db, _audit(db), repo=ClientResourceRepository(db))


def get_client_module_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClientModuleService:
    return ClientModuleService(db, _audit(db), repo=ClientModuleRepository(db))


def get_role_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> RoleService:
    return RoleService(
        db,
        _audit(db),
        repo=RoleRepositoryImpl(db),
        relation_repo=_relation(db),
        resource_service=get_resource_service(db),
        client_resource_service=get_client_resource_service(db),
        account_repo=_account_repo(db),
        profile_read_port=get_profile_read_port(db),
    )


def get_group_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> GroupService:
    return GroupService(
        db,
        _audit(db),
        repo=GroupRepositoryImpl(db),
        relation_repo=_relation(db),
        resource_service=get_resource_service(db),
        client_resource_service=get_client_resource_service(db),
        account_repo=_account_repo(db),
        role_repo=RoleRepositoryImpl(db),
    )


def get_account_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountService:
    # 延迟导入，打断 iam.wiring ↔ profile.wiring 循环
    from hei_fastapi_ddd.contexts.profile.infrastructure.wiring import (
        build_profile_identity_service,
    )

    repo = AccountRepositoryImpl(db)
    return AccountService(
        db,
        repo=repo,
        profile_port=ProfileUpsertAdapter(db),
        relation_repo=_relation(db),
        audit=_audit(db),
        read_service=AccountReadService(repo, ProfileReadAdapter(db)),
        resource_service=get_resource_service(db),
        client_resource_service=get_client_resource_service(db),
        role_repo=RoleRepositoryImpl(db),
        group_repo=GroupRepositoryImpl(db),
        identity_service=build_profile_identity_service(db),
    )


def get_password_history_port(db: AsyncSession) -> PasswordHistoryRepositoryImpl:
    return PasswordHistoryRepositoryImpl(db)
