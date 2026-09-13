""" Author: Charlie

文件相关 Schema：元数据响应、上传/创建载荷与查询参数。
"""

from datetime import datetime

from pydantic import Field

from hei_fastapi_ddd.shared.config.enums import StorageProvider
from hei_fastapi_ddd.shared.web.pagination import PageQuery
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireInt


class SysFileSchema(ApiSchema):
    """文件元数据响应模型，含创建/更新人昵称。"""

    id: str
    object_name: str
    original_name: str
    storage_provider: StorageProvider
    bucket: str | None = None
    content_type: str
    size: WireInt
    url: str
    created_at: datetime = Field(examples=["2026-06-17T12:00:00Z"])
    created_by: str | None = None
    updated_at: datetime = Field(examples=["2026-06-17T12:00:00Z"])
    updated_by: str | None = None

class FileUploadRequest(ApiSchema):
    """文件上传请求载荷，封装上传原文件信息和内容类型。"""

    filename: str
    content: bytes
    content_type: str
    storage_provider: StorageProvider | None = None
    category: str = ""
    object_name: str | None = None


class FileRecordCreate(ApiSchema):
    """文件元数据创建载荷，统一仓储层落库参数。"""

    object_name: str
    original_name: str
    storage_provider: StorageProvider
    bucket: str | None = None
    content_type: str
    size: WireInt
    url: str


class FileUpdateRequest(ApiSchema):
    """文件更新请求。"""

    id: str = Field(min_length=1, max_length=64)
    original_name: str = Field(min_length=1, max_length=255)


class FileAdminPageQuery(PageQuery):
    """文件后台分页查询参数。"""

    original_name: str | None = Field(default=None, max_length=255)
    object_name: str | None = Field(default=None, max_length=255)
    storage_provider: StorageProvider | None = None
    content_type: str | None = Field(default=None, max_length=128)


class ObjectNameQuery(ApiSchema):
    """对象名查询参数。"""

    object_name: str = Field(min_length=1, max_length=255)


class FileUrlRequest(ObjectNameQuery):
    """获取文件 URL 的请求参数。"""

    pass


class FileUrlResponse(ApiSchema):
    """文件 URL 响应。"""

    object_name: str
    url: str
