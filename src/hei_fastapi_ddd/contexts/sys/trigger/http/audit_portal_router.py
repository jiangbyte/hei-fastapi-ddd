"""门户端操作审计。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from hei_fastapi_ddd.contexts.sys.api.audit_schemas import (
    OperationAuditPageQuery,
    OperationAuditRecord,
)
from hei_fastapi_ddd.contexts.sys.application.audit.audit_application_service import (
    OperationAuditService,
)
from hei_fastapi_ddd.contexts.sys.application.audit.dto import (
    OperationAuditPageQuery as OperationAuditPageQueryDto,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.wiring import get_audit_service
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import get_current_session, require_account_type
from hei_fastapi_ddd.shared.schema.base import IdQuery
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


def _map_page(page: PageData[dict]) -> PageData[OperationAuditRecord]:
    return PageData(
        current=page.current,
        size=page.size,
        total=page.total,
        records=[OperationAuditRecord.model_validate(r) for r in page.records],
    )


@router.get(
    "/v1/portal/sys/audit/my-page",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[PageData[OperationAuditRecord]],
    response_model_exclude_none=False,
)
async def my_page(
    query: Annotated[OperationAuditPageQuery, Depends()],
    session: Annotated[SessionPayload, Depends(get_current_session)],
    service: Annotated[OperationAuditService, Depends(get_audit_service)],
) -> ApiResponse[PageData[OperationAuditRecord]]:
    return success(
        _map_page(
            await service.my_page(
                OperationAuditPageQueryDto.model_validate(query.model_dump()),
                session.account_id,
            )
        )
    )


@router.get(
    "/v1/portal/sys/audit/my-detail",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[OperationAuditRecord],
    response_model_exclude_none=False,
)
async def my_detail(
    query: Annotated[IdQuery, Depends()],
    session: Annotated[SessionPayload, Depends(get_current_session)],
    service: Annotated[OperationAuditService, Depends(get_audit_service)],
) -> ApiResponse[OperationAuditRecord]:
    return success(
        OperationAuditRecord.model_validate(
            await service.my_detail(query.id, session.account_id)
        )
    )
