"""文件应用层 DTO。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from hei_fastapi_ddd.shared.web.pagination import PageQuery


class FileUploadCommand(BaseModel):
    """上传命令。"""

    model_config = ConfigDict(extra="ignore")

    filename: str
    content: bytes
    content_type: str
    storage_provider: str | None = None
    category: str = ""
    object_name: str | None = None


class FileUpdateCommand(BaseModel):
    """更新命令。"""

    model_config = ConfigDict(extra="ignore")

    id: str
    original_name: str


class FileAdminPageQuery(PageQuery):
    """后台分页。"""

    model_config = ConfigDict(extra="ignore")

    original_name: str | None = None
    object_name: str | None = None
    storage_provider: str | None = None
    content_type: str | None = None


class ObjectNameQuery(BaseModel):
    """对象名查询。"""

    model_config = ConfigDict(extra="ignore")

    object_name: str
