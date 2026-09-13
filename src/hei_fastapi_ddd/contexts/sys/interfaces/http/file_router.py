""" Author: Charlie

文件管理端接口：上传、删除、更新、详情、URL、签名地址与分页。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType, StorageProvider
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.web.pagination import PageData
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.deps.auth import get_current_session, require_account_type, require_permission
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.sys.interfaces.http.file_schemas import (
    FileAdminPageQuery,
    FileUpdateRequest,
    FileUploadRequest,
    FileUrlRequest,
    FileUrlResponse,
    SysFileSchema,
)
from hei_fastapi_ddd.contexts.sys.application.file.file_application_service import FileService

router = APIRouter()


@router.post(
    "/v1/admin/sys/file/upload",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:file:upload")),
    ],
    response_model=ApiResponse[SysFileSchema],
)
async def upload(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    storage_provider: Annotated[StorageProvider | None, Query()] = None,
) -> ApiResponse[SysFileSchema]:
    """上传文件并返回元数据。"""
    content = await file.read(settings.storage.upload_max_bytes + 1)
    return success(
        await FileService(db).upload(
            FileUploadRequest(
                filename=file.filename or "file.bin",
                content=content,
                content_type=file.content_type or "application/octet-stream",
                storage_provider=storage_provider,
            )
        )
    )


@router.post(
    "/v1/admin/sys/file/delete",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:file:delete")),
    ],
    response_model=ApiResponse[None],
)
async def delete(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """批量删除文件。"""
    await FileService(db).delete(payload)
    return success()


@router.post(
    "/v1/admin/sys/file/update",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:file:update")),
    ],
    response_model=ApiResponse[None],
)
async def update(
    payload: FileUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """更新文件信息。"""
    await FileService(db).update(payload)
    return success()


@router.get(
    "/v1/admin/sys/file/detail",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:file:detail")),
    ],
    response_model=ApiResponse[SysFileSchema],
)
async def detail(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[SysFileSchema]:
    """查询文件元数据详情。"""
    return success(await FileService(db).detail(query))


@router.post(
    "/v1/admin/sys/file/list_by_ids",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:file:detail")),
    ],
    response_model=ApiResponse[list[SysFileSchema]],
)
async def list_by_ids(
    payload: IdsRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[SysFileSchema]]:
    """按 ID 列表批量查询文件元数据。"""
    return success(await FileService(db).list_by_ids(payload))


@router.get(
    "/v1/admin/sys/file/download",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:file:url")),
    ],
    response_class=Response,
)
async def download(
    query: Annotated[IdQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    """按 ID 下载文件。"""
    return await FileService(db).download_by_id(query)


@router.post(
    "/v1/admin/sys/file/url",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:file:url")),
    ],
    response_model=ApiResponse[FileUrlResponse],
)
async def url(
    payload: FileUrlRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[FileUrlResponse]:
    """获取文件的访问 URL。"""
    return success(
        FileUrlResponse(
            object_name=payload.object_name,
            url=await FileService(db).get_url(payload),
        )
    )


@router.post(
    "/v1/admin/sys/file/presigned_url",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:file:presignedurl")),
    ],
    response_model=ApiResponse[FileUrlResponse],
)
async def presigned_url(
    payload: FileUrlRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[FileUrlResponse]:
    """获取文件的签名访问 URL。"""
    return success(
        FileUrlResponse(
            object_name=payload.object_name,
            url=await FileService(db).get_presigned_url(payload),
        )
    )


@router.get(
    "/v1/admin/sys/file/page",
    dependencies=[
        Depends(require_account_type(AccountType.ADMIN)),
        Depends(require_permission("sys:file:page")),
    ],
    response_model=ApiResponse[PageData[SysFileSchema]],
)
async def page(
    query: Annotated[FileAdminPageQuery, Depends()],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[PageData[SysFileSchema]]:
    """分页查询文件元数据（按数据权限过滤）。"""
    return success(await FileService(db).page(query, session))
