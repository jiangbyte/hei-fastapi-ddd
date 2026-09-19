"""部门管理 HTTP 路由：Schema ↔ Command。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from hei_fastapi_ddd.contexts.iam.api.dept_schemas import (
    DeptAdminPageQuery,
    DeptCreateRequest,
    DeptTreeNode,
    DeptUpdateRequest,
    SysDeptSchema,
)
from hei_fastapi_ddd.contexts.iam.application.dept.dept_application_service import DeptService
from hei_fastapi_ddd.contexts.iam.application.dept.dto import (
    DeptCreateCommand,
    DeptPageQuery,
    DeptUpdateCommand,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.wiring import get_dept_service
from hei_fastapi_ddd.contexts.iam.trigger.assembler.dept_assembler import (
    build_dept_tree_nodes,
    to_dept_schema,
    to_dept_schema_page,
)
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import (
    get_current_session,
    require_account_type,
    require_permission,
)
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.post(
    "/v1/admin/sys/depts/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: DeptCreateRequest,
    service: Annotated[DeptService, Depends(get_dept_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.create(DeptCreateCommand.model_validate(payload.model_dump()), session=session)
    return success()


@router.post(
    "/v1/admin/sys/depts/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: DeptUpdateRequest,
    service: Annotated[DeptService, Depends(get_dept_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.update(DeptUpdateCommand.model_validate(payload.model_dump()), session=session)
    return success()


@router.post(
    "/v1/admin/sys/depts/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    service: Annotated[DeptService, Depends(get_dept_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.delete(payload, session=session)
    return success()


@router.get(
    "/v1/admin/sys/depts/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:detail")),
    ],
    response_model=ApiResponse[SysDeptSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[DeptService, Depends(get_dept_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysDeptSchema]:
    return success(to_dept_schema(await service.detail(query, session=session)))


@router.get(
    "/v1/admin/sys/depts/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:page")),
    ],
    response_model=ApiResponse[PageData[SysDeptSchema]],
)
async def page(
    query: Annotated[DeptAdminPageQuery, Depends()],
    service: Annotated[DeptService, Depends(get_dept_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[SysDeptSchema]]:
    page_data = await service.page_admin(
        DeptPageQuery.model_validate(query.model_dump()),
        session=session,
    )
    return success(
        PageData(
            records=to_dept_schema_page(page_data.records),
            total=page_data.total,
            current=page_data.current,
            size=page_data.size,
        )
    )


@router.get(
    "/v1/admin/sys/depts/tree",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("iam:dept:tree")),
    ],
    response_model=ApiResponse[list[DeptTreeNode]],
)
async def tree(
    service: Annotated[DeptService, Depends(get_dept_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[list[DeptTreeNode]]:
    return success(build_dept_tree_nodes(await service.list_dept_tree(session=session)))
