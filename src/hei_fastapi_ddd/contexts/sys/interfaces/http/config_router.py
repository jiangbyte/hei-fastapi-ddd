""" Author: Charlie

系统配置管理端接口：配置增删改查、批量保存与告警通知测试。
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.schema.base import ApiSchema, IdQuery, IdsRequest
from hei_fastapi_ddd.shared.deps.auth import require_account_type, require_permission
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.sys.application.audit.alert import send_test_webhook
from hei_fastapi_ddd.contexts.sys.interfaces.http.config_schemas import (
    CategoryQuery,
    ConfigAdminPageQuery,
    ConfigBatchSaveRequest,
    ConfigCreateRequest,
    ConfigUpdateRequest,
    SysConfigSchema,
)
from hei_fastapi_ddd.contexts.sys.application.config.config_application_service import ConfigService


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
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """新增系统配置。"""
    await ConfigService(db).create(payload)
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
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """更新系统配置。"""
    await ConfigService(db).update(payload)
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
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """批量删除系统配置。"""
    await ConfigService(db).delete(payload)
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
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysConfigSchema]:
    """查询配置详情。"""
    return success(await ConfigService(db).detail(query))


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
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageData[SysConfigSchema]]:
    """后台分页查询系统配置。"""
    return success(await ConfigService(db).page_admin(query))


@router.get(
    "/v1/admin/sys/config/list",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:config:page")),
    ],
    response_model=ApiResponse[list[SysConfigSchema]],
)
async def list_config(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[CategoryQuery, Depends()],
) -> ApiResponse[list[SysConfigSchema]]:
    """按分类/作用域查询配置列表。"""
    return success(await ConfigService(db).list_by_category(query))


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
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """批量保存系统配置。"""
    await ConfigService(db).batch_save(payload)
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
        from hei_fastapi_ddd.shared.exceptions.business import BusinessError

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
        from hei_fastapi_ddd.shared.exceptions.business import BusinessError

        raise BusinessError(err)
    return success({"message": "测试消息已发送"})
