""" Author: Charlie

文件公开端接口：上传、下载、详情、URL 与签名地址。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from hei_fastapi_ddd.contexts.sys.api.file_schemas import (
    FileUploadRequest,
    FileUrlRequest,
    FileUrlResponse,
    SysFileSchema,
)
from hei_fastapi_ddd.contexts.sys.application.file.file_application_service import FileService
from hei_fastapi_ddd.shared.config.enums import AccountType, StorageProvider
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.deps.auth import get_current_session, require_account_type
from hei_fastapi_ddd.contexts.sys.infrastructure.wiring import get_file_service
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.storage.url import normalize_object_name
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()
# 公开端接口统一要求 PORTAL 账户登录。
portal_dependencies = [Depends(require_account_type(AccountType.PORTAL))]


@router.post(
    "/v1/portal/sys/file/upload",
    dependencies=portal_dependencies,
    response_model=ApiResponse[SysFileSchema],
)
async def upload(
    file: Annotated[UploadFile, File(...)],
    service: Annotated[FileService, Depends(get_file_service)],
    storage_provider: Annotated[StorageProvider | None, Query()] = None,
) -> ApiResponse[SysFileSchema]:
    """上传文件并返回元数据。"""
    content = await file.read(settings.storage.upload_max_bytes + 1)
    return success(
        await service.upload(
            FileUploadRequest(
                filename=file.filename or "file.bin",
                content=content,
                content_type=file.content_type or "application/octet-stream",
                storage_provider=storage_provider,
            )
        )
    )


@router.get(
    "/v1/portal/sys/file/detail",
    dependencies=portal_dependencies,
    response_model=ApiResponse[SysFileSchema],
)
async def detail(
    service: Annotated[FileService, Depends(get_file_service)],
    query: Annotated[IdQuery, Depends()],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[SysFileSchema]:
    """查询文件元数据详情（仅本人上传的文件，对齐 hei-boot 归属校验）。"""
    return success(await service.detail(query, session=session))


@router.post(
    "/v1/portal/sys/file/list_by_ids",
    dependencies=portal_dependencies,
    response_model=ApiResponse[list[SysFileSchema]],
)
async def list_by_ids(
    payload: IdsRequest,
    service: Annotated[FileService, Depends(get_file_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[list[SysFileSchema]]:
    """按 ID 列表批量查询文件元数据（仅本人上传的文件）。"""
    return success(await service.list_by_ids(payload, session=session))


@router.get(
    "/v1/portal/sys/file/download",
    dependencies=portal_dependencies,
    response_class=Response,
)
async def download(
    service: Annotated[FileService, Depends(get_file_service)],
    query: Annotated[IdQuery, Depends()],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> Response:
    """按 ID 下载文件（仅本人上传的文件）。"""
    return await service.download_by_id(query, session=session)


@router.post(
    "/v1/portal/sys/file/url",
    dependencies=portal_dependencies,
    response_model=ApiResponse[FileUrlResponse],
)
async def url(
    payload: FileUrlRequest,
    service: Annotated[FileService, Depends(get_file_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[FileUrlResponse]:
    """获取文件的访问 URL（仅本人上传的文件，object_name 归一化返回）。"""
    normalized = normalize_object_name(payload.object_name)
    return success(
        FileUrlResponse(
            object_name=normalized,
            url=await service.get_url(payload, session=session),
        )
    )


@router.post(
    "/v1/portal/sys/file/presigned_url",
    dependencies=portal_dependencies,
    response_model=ApiResponse[FileUrlResponse],
)
async def presigned_url(
    payload: FileUrlRequest,
    service: Annotated[FileService, Depends(get_file_service)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
) -> ApiResponse[FileUrlResponse]:
    """获取文件的签名访问 URL（仅本人上传的文件，object_name 归一化返回）。"""
    normalized = normalize_object_name(payload.object_name)
    return success(
        FileUrlResponse(
            object_name=normalized,
            url=await service.get_presigned_url(payload, session=session),
        )
    )
