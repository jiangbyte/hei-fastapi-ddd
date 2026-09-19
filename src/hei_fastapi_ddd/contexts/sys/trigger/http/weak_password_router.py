""" Author: Charlie

弱密码库管理端接口。
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from hei_fastapi_ddd.contexts.sys.api.weak_password_schemas import (
    SysWeakPasswordSchema,
    WeakPasswordAdminPageQuery,
    WeakPasswordCreateRequest,
    WeakPasswordListQuery,
    WeakPasswordUpdateRequest,
)
from hei_fastapi_ddd.contexts.sys.application.weak_password.dto import (
    WeakPasswordAdminPageQuery as WeakPasswordAdminPageQueryDto,
    WeakPasswordCreateCommand,
    WeakPasswordIdsCommand,
    WeakPasswordListQuery as WeakPasswordListQueryDto,
    WeakPasswordUpdateCommand,
)
from hei_fastapi_ddd.contexts.sys.application.weak_password.weak_password_application_service import (
    WeakPasswordService,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.wiring import get_weak_password_service
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import require_account_type, require_permission
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.post(
    "/v1/admin/sys/weak-password/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: WeakPasswordCreateRequest,
    service: Annotated[WeakPasswordService, Depends(get_weak_password_service)],
) -> ApiResponse[None]:
    """新增弱密码。"""
    await service.create(WeakPasswordCreateCommand.model_validate(payload.model_dump()))
    return success()


@router.post(
    "/v1/admin/sys/weak-password/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: WeakPasswordUpdateRequest,
    service: Annotated[WeakPasswordService, Depends(get_weak_password_service)],
) -> ApiResponse[None]:
    """更新弱密码。"""
    await service.update(WeakPasswordUpdateCommand.model_validate(payload.model_dump()))
    return success()


@router.post(
    "/v1/admin/sys/weak-password/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    service: Annotated[WeakPasswordService, Depends(get_weak_password_service)],
) -> ApiResponse[None]:
    """批量删除弱密码。"""
    await service.delete(WeakPasswordIdsCommand(ids=list(payload.ids)))
    return success()


@router.get(
    "/v1/admin/sys/weak-password/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:detail")),
    ],
    response_model=ApiResponse[SysWeakPasswordSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[WeakPasswordService, Depends(get_weak_password_service)],
) -> ApiResponse[SysWeakPasswordSchema]:
    """查询弱密码详情。"""
    return success(SysWeakPasswordSchema.model_validate(await service.detail(query.id)))


@router.get(
    "/v1/admin/sys/weak-password/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:page")),
    ],
    response_model=ApiResponse[PageData[SysWeakPasswordSchema]],
)
async def page(
    query: Annotated[WeakPasswordAdminPageQuery, Depends()],
    service: Annotated[WeakPasswordService, Depends(get_weak_password_service)],
) -> ApiResponse[PageData[SysWeakPasswordSchema]]:
    """分页查询弱密码。"""
    page_data = await service.page_admin(
        WeakPasswordAdminPageQueryDto.model_validate(query.model_dump())
    )
    records = [SysWeakPasswordSchema.model_validate(row) for row in page_data.records]
    return success(
        PageData(
            size=page_data.size,
            current=page_data.current,
            total=page_data.total,
            pages=page_data.pages,
            records=records,
        )
    )


@router.get(
    "/v1/admin/sys/weak-password/list",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:weakpassword:list")),
    ],
    response_model=ApiResponse[list[SysWeakPasswordSchema]],
)
async def list_all(
    query: Annotated[WeakPasswordListQuery, Depends()],
    service: Annotated[WeakPasswordService, Depends(get_weak_password_service)],
) -> ApiResponse[list[SysWeakPasswordSchema]]:
    """列出全部弱密码。"""
    rows = await service.list_all(WeakPasswordListQueryDto.model_validate(query.model_dump()))
    return success([SysWeakPasswordSchema.model_validate(row) for row in rows])
