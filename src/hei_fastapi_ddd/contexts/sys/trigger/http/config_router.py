""" Author: Charlie

系统配置管理端接口：配置增删改查、批量保存与告警通知测试。
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from pydantic import Field
from hei_fastapi_ddd.contexts.sys.api.config_schemas import (
    CategoryQuery,
    ConfigAdminPageQuery,
    ConfigBatchSaveRequest,
    ConfigCreateRequest,
    ConfigUpdateRequest,
    SysConfigSchema,
)
from hei_fastapi_ddd.contexts.sys.application.audit.alert import send_test_webhook
from hei_fastapi_ddd.contexts.sys.application.config.config_application_service import ConfigService
from hei_fastapi_ddd.contexts.sys.application.config.dto import (
    CategoryQuery as CategoryQueryDto,
    ConfigAdminPageQuery as ConfigAdminPageQueryDto,
    ConfigBatchSaveCommand,
    ConfigCreateCommand,
    ConfigUpdateCommand,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.wiring import get_config_service
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.deps.auth import require_account_type, require_permission
from hei_fastapi_ddd.shared.schema.base import ApiSchema, IdQuery, IdsRequest
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success


class TestWebhookRequest(ApiSchema):
    """审计告警 Webhook 测试请求。"""

    webhook_url: str = Field(default="", max_length=1024)
    webhook_secret: str = Field(default="", max_length=256)


router = APIRouter()


@router.post(
    "/v1/admin/sys/config/create",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:config:create")),
    ],
    response_model=ApiResponse[None],
)
async def create(
    payload: ConfigCreateRequest,
    service: Annotated[ConfigService, Depends(get_config_service)],
) -> ApiResponse[None]:
    """新增系统配置。"""
    await service.create(ConfigCreateCommand.model_validate(payload.model_dump()))
    return success()


@router.post(
    "/v1/admin/sys/config/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:config:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: ConfigUpdateRequest,
    service: Annotated[ConfigService, Depends(get_config_service)],
) -> ApiResponse[None]:
    """更新系统配置。"""
    await service.update(ConfigUpdateCommand.model_validate(payload.model_dump()))
    return success()


@router.post(
    "/v1/admin/sys/config/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:config:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    service: Annotated[ConfigService, Depends(get_config_service)],
) -> ApiResponse[None]:
    """批量删除系统配置。"""
    await service.delete(list(payload.ids))
    return success()


@router.get(
    "/v1/admin/sys/config/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:config:detail")),
    ],
    response_model=ApiResponse[SysConfigSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[ConfigService, Depends(get_config_service)],
) -> ApiResponse[SysConfigSchema]:
    """查询配置详情。"""
    return success(SysConfigSchema.model_validate(await service.detail(query.id)))


@router.get(
    "/v1/admin/sys/config/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:config:page")),
    ],
    response_model=ApiResponse[PageData[SysConfigSchema]],
)
async def page(
    query: Annotated[ConfigAdminPageQuery, Depends()],
    service: Annotated[ConfigService, Depends(get_config_service)],
) -> ApiResponse[PageData[SysConfigSchema]]:
    """后台分页查询系统配置。"""
    page_data = await service.page_admin(
        ConfigAdminPageQueryDto.model_validate(query.model_dump())
    )
    records = [SysConfigSchema.model_validate(row) for row in page_data.records]
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
    "/v1/admin/sys/config/list",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:config:page")),
    ],
    response_model=ApiResponse[list[SysConfigSchema]],
)
async def list_config(
    query: Annotated[CategoryQuery, Depends()],
    service: Annotated[ConfigService, Depends(get_config_service)],
) -> ApiResponse[list[SysConfigSchema]]:
    """按分类/作用域查询配置列表。"""
    rows = await service.list_by_category(CategoryQueryDto.model_validate(query.model_dump()))
    return success([SysConfigSchema.model_validate(row) for row in rows])


@router.post(
    "/v1/admin/sys/config/batch-save",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:config:update")),
    ],
    response_model=ApiResponse[None],
)
async def batch_save(
    payload: ConfigBatchSaveRequest,
    service: Annotated[ConfigService, Depends(get_config_service)],
) -> ApiResponse[None]:
    """批量保存系统配置。"""
    await service.batch_save(ConfigBatchSaveCommand.model_validate(payload.model_dump()))
    return success()


@router.post(
    "/v1/admin/sys/config/audit-alert/test-webhook",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
)
async def test_audit_alert_webhook(
    payload: Annotated[TestWebhookRequest, Body()] = TestWebhookRequest(),
) -> ApiResponse[dict]:
    """发送审计告警测试 Webhook（请求体可省略，对齐 hei-boot），失败时抛出业务错误。"""
    err = await send_test_webhook(payload.webhook_url, payload.webhook_secret)
    if err:
        from hei_fastapi_ddd.types.business import BusinessError

        raise BusinessError(err)
    return success({"message": "测试消息已发送"})


@router.post(
    "/v1/admin/sys/config/audit-alert/test-push",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
)
async def test_audit_alert_push() -> ApiResponse[dict]:
    """发送审计告警测试推送，失败时抛出业务错误。"""
    from hei_fastapi_ddd.contexts.sys.application.audit.alert import send_test_push

    err = await send_test_push()
    if err:
        from hei_fastapi_ddd.types.business import BusinessError

        raise BusinessError(err)
    return success({"message": "测试消息已发送"})
