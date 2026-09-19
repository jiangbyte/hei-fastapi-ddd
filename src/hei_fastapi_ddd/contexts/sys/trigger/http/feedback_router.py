"""反馈路由：管理端 CRUD、提交与「我的反馈」接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from hei_fastapi_ddd.contexts.sys.api.feedback_schemas import (
    MyFeedbackPageQuery,
    SysFeedbackAdminPageQuery,
    SysFeedbackCreateRequest,
    SysFeedbackSchema,
    SysFeedbackUpdateRequest,
)
from hei_fastapi_ddd.contexts.sys.application.feedback.dto import (
    FeedbackAdminPageQuery,
    FeedbackCreateCommand,
    FeedbackIdQuery,
    FeedbackIdsCommand,
    FeedbackUpdateCommand,
    MyFeedbackPageQuery as MyFeedbackPageQueryDto,
)
from hei_fastapi_ddd.contexts.sys.application.feedback.feedback_application_service import (
    SysFeedbackService,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.wiring import get_feedback_service
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

admin_router = APIRouter()
portal_router = APIRouter()


def _map_page(page: PageData[dict]) -> PageData[SysFeedbackSchema]:
    return PageData(
        current=page.current,
        size=page.size,
        total=page.total,
        records=[SysFeedbackSchema.model_validate(r) for r in page.records],
    )


@admin_router.get(
    "/v1/admin/sys/feedbacks/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:feedback:page")),
    ],
    response_model=ApiResponse[PageData[SysFeedbackSchema]],
)
async def page(
    query: Annotated[SysFeedbackAdminPageQuery, Depends()],
    service: Annotated[SysFeedbackService, Depends(get_feedback_service)],
) -> ApiResponse[PageData[SysFeedbackSchema]]:
    return success(
        _map_page(
            await service.page_admin(
                FeedbackAdminPageQuery.model_validate(query.model_dump())
            )
        )
    )


@admin_router.get(
    "/v1/admin/sys/feedbacks/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:feedback:detail")),
    ],
    response_model=ApiResponse[SysFeedbackSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[SysFeedbackService, Depends(get_feedback_service)],
) -> ApiResponse[SysFeedbackSchema]:
    return success(
        SysFeedbackSchema.model_validate(
            await service.detail(FeedbackIdQuery(id=query.id))
        )
    )


@admin_router.post(
    "/v1/admin/sys/feedbacks/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:feedback:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: SysFeedbackUpdateRequest,
    service: Annotated[SysFeedbackService, Depends(get_feedback_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.update(
        FeedbackUpdateCommand.model_validate(payload.model_dump()), session
    )
    return success()


@admin_router.post(
    "/v1/admin/sys/feedbacks/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:feedback:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    service: Annotated[SysFeedbackService, Depends(get_feedback_service)],
) -> ApiResponse[None]:
    await service.delete(FeedbackIdsCommand(ids=payload.ids))
    return success()


@admin_router.post(
    "/v1/admin/sys/feedbacks/submit",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[None],
)
async def admin_submit(
    payload: SysFeedbackCreateRequest,
    service: Annotated[SysFeedbackService, Depends(get_feedback_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.submit(
        FeedbackCreateCommand.model_validate(payload.model_dump()), session
    )
    return success()


@admin_router.get(
    "/v1/admin/sys/feedbacks/my-page",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[PageData[SysFeedbackSchema]],
)
async def admin_my_page(
    query: Annotated[MyFeedbackPageQuery, Depends()],
    service: Annotated[SysFeedbackService, Depends(get_feedback_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[SysFeedbackSchema]]:
    return success(
        _map_page(
            await service.page_my(
                MyFeedbackPageQueryDto.model_validate(query.model_dump()), session
            )
        )
    )


@admin_router.get(
    "/v1/admin/sys/feedbacks/my-detail",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[SysFeedbackSchema],
)
async def admin_my_detail(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[SysFeedbackService, Depends(get_feedback_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysFeedbackSchema]:
    return success(
        SysFeedbackSchema.model_validate(
            await service.detail_my(FeedbackIdQuery(id=query.id), session)
        )
    )


@portal_router.post(
    "/v1/portal/sys/feedbacks/submit",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[None],
)
async def submit(
    payload: SysFeedbackCreateRequest,
    service: Annotated[SysFeedbackService, Depends(get_feedback_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[None]:
    await service.submit(
        FeedbackCreateCommand.model_validate(payload.model_dump()), session
    )
    return success()


@portal_router.get(
    "/v1/portal/sys/feedbacks/my-page",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[PageData[SysFeedbackSchema]],
)
async def my_page(
    query: Annotated[MyFeedbackPageQuery, Depends()],
    service: Annotated[SysFeedbackService, Depends(get_feedback_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[SysFeedbackSchema]]:
    return success(
        _map_page(
            await service.page_my(
                MyFeedbackPageQueryDto.model_validate(query.model_dump()), session
            )
        )
    )


@portal_router.get(
    "/v1/portal/sys/feedbacks/my-detail",
    dependencies=[Depends(require_account_type(AccountType.PORTAL))],
    response_model=ApiResponse[SysFeedbackSchema],
)
async def my_detail(
    query: Annotated[IdQuery, Depends()],
    service: Annotated[SysFeedbackService, Depends(get_feedback_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysFeedbackSchema]:
    return success(
        SysFeedbackSchema.model_validate(
            await service.detail_my(FeedbackIdQuery(id=query.id), session)
        )
    )
