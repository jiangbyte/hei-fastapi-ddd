"""sys 限界上下文依赖装配。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.audit.audit_application_service import (
    OperationAuditService,
)
from hei_fastapi_ddd.contexts.sys.application.banner.banner_application_service import (
    BannerService,
)
from hei_fastapi_ddd.contexts.sys.application.codegen.codegen_application_service import (
    CodegenService,
)
from hei_fastapi_ddd.contexts.sys.application.config.config_application_service import ConfigService
from hei_fastapi_ddd.contexts.sys.application.dict.dict_application_service import DictService
from hei_fastapi_ddd.contexts.sys.application.feedback.feedback_application_service import (
    SysFeedbackService,
)
from hei_fastapi_ddd.contexts.sys.application.file.file_application_service import FileService
from hei_fastapi_ddd.contexts.sys.application.job.job_application_service import JobService
from hei_fastapi_ddd.contexts.sys.application.notice.notice_application_service import (
    SysNoticeService,
)
from hei_fastapi_ddd.contexts.sys.application.weak_password.weak_password_application_service import (
    WeakPasswordService,
)
from hei_fastapi_ddd.contexts.sys.application.workspace.workspace_application_service import (
    WorkspaceService,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.job.runner import JobRunnerImpl
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_repository import (
    OperationAuditRepositoryImpl,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.banner_repository import (
    BannerRepositoryImpl,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.codegen_repository import (
    CodegenRepositoryImpl,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.config_repository import (
    ConfigRepositoryImpl,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.dict_repository import (
    DictRepositoryImpl,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.feedback_repository import (
    SysFeedbackRepositoryImpl,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.file_repository import (
    FileRepositoryImpl,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.job_repository import (
    JobLogRepositoryImpl,
    JobRepositoryImpl,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.notice_repository import (
    SysNoticeRepositoryImpl,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.weak_password_repository import (
    WeakPasswordRepositoryImpl,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.workspace_repository import (
    WorkspaceShortcutRepositoryImpl,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.read.account_identity_read_adapter import (
    AccountIdentityReadAdapter,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.read.workspace_read_adapter import (
    WorkspaceReadAdapter,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session


def build_job_service(db: AsyncSession) -> JobService:
    return JobService(db, JobRepositoryImpl(db), JobLogRepositoryImpl(db), JobRunnerImpl())


def get_dict_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> DictService:
    return DictService(db, DictRepositoryImpl(db))


def get_weak_password_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> WeakPasswordService:
    return WeakPasswordService(db, WeakPasswordRepositoryImpl(db))


def get_config_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> ConfigService:
    return ConfigService(db, ConfigRepositoryImpl(db))


def get_notice_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SysNoticeService:
    return SysNoticeService(db, SysNoticeRepositoryImpl(db))


def get_file_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> FileService:
    return FileService(db, FileRepositoryImpl(db))


def get_job_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> JobService:
    return build_job_service(db)


def build_audit_service(db: AsyncSession) -> OperationAuditService:
    return OperationAuditService(db, OperationAuditRepositoryImpl(db))


def get_audit_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> OperationAuditService:
    return build_audit_service(db)


def build_banner_service(db: AsyncSession) -> BannerService:
    return BannerService(db, BannerRepositoryImpl(db), FileService(db, FileRepositoryImpl(db)))


def get_banner_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> BannerService:
    return build_banner_service(db)


def get_feedback_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SysFeedbackService:
    file_repo = FileRepositoryImpl(db)
    file_service = FileService(db, file_repo)
    from hei_fastapi_ddd.contexts.profile.infrastructure.api.profile_read_adapter import (
        get_profile_read_port,
    )

    return SysFeedbackService(
        db,
        SysFeedbackRepositoryImpl(db),
        file_repo,
        file_service,
        profile_read_port=get_profile_read_port(db),
    )


def get_codegen_service(db: Annotated[AsyncSession, Depends(get_db_session)]) -> CodegenService:
    return CodegenService(db, CodegenRepositoryImpl(db))


def get_workspace_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceService:
    return WorkspaceService(db, WorkspaceShortcutRepositoryImpl(db), WorkspaceReadAdapter(db))


def get_account_identity_reader(db: AsyncSession) -> AccountIdentityReadAdapter:
    return AccountIdentityReadAdapter(db)
