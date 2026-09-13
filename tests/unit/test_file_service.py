""" Author: Charlie

文件服务单测：使用内存假存储替代 LOCAL。
"""

from __future__ import annotations

from sqlalchemy import select

from hei_fastapi_ddd.contexts.sys.application.file.file_application_service import FileService
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.file_po import SysFile
from hei_fastapi_ddd.contexts.sys.interfaces.http.file_schemas import (
    FileUploadRequest,
    ObjectNameQuery,
)
from hei_fastapi_ddd.shared.config.enums import StorageProvider
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.schema.base import IdQuery
from hei_fastapi_ddd.shared.schema.datetime import format_utc_iso8601
from hei_fastapi_ddd.shared.storage.config import StorageConfig


class _MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.config = StorageConfig(
            id="memory",
            name="memory",
            provider=StorageProvider.MINIO,
            bucket="test",
            bucket_public=True,
            base_url="https://cdn.example.com",
            is_default=True,
        )

    def upload_bytes(self, object_name: str, content: bytes, content_type: str = "") -> str:
        self.objects[object_name] = content
        return self.get_object_url(object_name)

    def delete_object(self, object_name: str) -> None:
        self.objects.pop(object_name, None)

    def get_object_url(self, object_name: str) -> str:
        return f"{self.config.base_url.rstrip('/')}/{object_name}"

    def get_presigned_url(self, object_name: str) -> str:
        return f"{self.get_object_url(object_name)}?X-Amz-Signature=test"

    def get_object_bytes(self, object_name: str) -> bytes:
        return self.objects[object_name]


def _install_memory_storage(monkeypatch) -> _MemoryStorage:
    storage = _MemoryStorage()
    config = storage.config
    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.sys.application.file.file_application_service.resolve_storage_config", lambda *a, **k: config
    )
    monkeypatch.setattr("hei_fastapi_ddd.contexts.sys.application.file.file_application_service.get_storage", lambda *a, **k: storage)
    monkeypatch.setattr(settings.storage, "provider", StorageProvider.MINIO)
    return storage


async def test_file_service_upload_and_url(monkeypatch, db_session):
    storage = _install_memory_storage(monkeypatch)
    service = FileService(db_session)
    entity = await service.upload(
        FileUploadRequest(filename="avatar.png", content=b"hello", content_type="image/png")
    )
    await db_session.commit()
    assert entity.object_name.startswith("uploads/")
    assert entity.object_name.endswith(".png")
    # 响应 url 为解析后的访问地址；库内 url 存 object key（对齐 hei-boot）。
    assert entity.url == f"https://cdn.example.com/{entity.object_name}"
    assert entity.object_name in storage.objects
    assert format_utc_iso8601(entity.created_at).endswith("Z")
    assert await service.get_url(ObjectNameQuery(object_name=entity.object_name)) == entity.url
    stored = (await db_session.execute(select(SysFile).where(SysFile.id == entity.id))).scalar_one()
    assert stored.original_name == "avatar.png"
    assert stored.url == entity.object_name
    await service.delete_by_object_name(entity.object_name)
    deleted = (
        await db_session.execute(select(SysFile).where(SysFile.id == entity.id))
    ).scalar_one_or_none()
    assert deleted is None
    assert entity.object_name not in storage.objects


async def test_file_service_download_has_content_disposition(monkeypatch, db_session):
    _install_memory_storage(monkeypatch)
    service = FileService(db_session)
    entity = await service.upload(
        FileUploadRequest(filename="报告.png", content=b"png", content_type="image/png")
    )
    await db_session.commit()
    response = await service.download_by_id(IdQuery(id=entity.id))
    assert response.body == b"png"
    assert "filename*=UTF-8''" in response.headers["Content-Disposition"]


async def test_resolve_access_url_uses_sys_file_provider(monkeypatch, db_session):
    """解析应按 sys_file.storage_provider 选引擎，而非盲目默认引擎。"""
    default_storage = _MemoryStorage()
    s3_storage = _MemoryStorage()
    s3_storage.config = StorageConfig(
        id="s3-alt",
        name="s3-alt",
        provider=StorageProvider.S3,
        bucket="alt",
        bucket_public=True,
        base_url="https://s3-alt.example.com",
        is_default=False,
    )

    def _resolve_config(*, provider=None, config_id=None, allow_settings_fallback=True):
        provider_value = getattr(provider, "value", provider)
        if provider_value in {StorageProvider.S3, "s3"} or config_id == "s3-alt":
            return s3_storage.config
        return default_storage.config

    def _get_storage(config_id=None, **kwargs):
        if config_id == "s3-alt" or kwargs.get("provider") in {StorageProvider.S3, "s3"}:
            return s3_storage
        return default_storage

    monkeypatch.setattr("hei_fastapi_ddd.contexts.sys.application.file.file_application_service.resolve_storage_config", _resolve_config)
    monkeypatch.setattr("hei_fastapi_ddd.contexts.sys.application.file.file_application_service.get_storage", _get_storage)
    monkeypatch.setattr(settings.storage, "provider", StorageProvider.MINIO)

    key = "uploads/2026/01/01/avatar-provider.png"
    row = SysFile(
        object_name=key,
        original_name="avatar-provider.png",
        storage_provider=StorageProvider.S3.value,
        bucket="alt",
        content_type="image/png",
        size=4,
        url=key,
    )
    db_session.add(row)
    await db_session.commit()

    service = FileService(db_session)
    resolved = await service.resolve_access_url(key)
    assert resolved == f"https://s3-alt.example.com/{key}"

    batch = await service.resolve_access_urls([key, None, "https://cdn.example.com/x.png"])
    assert batch[key] == f"https://s3-alt.example.com/{key}"
    assert batch["https://cdn.example.com/x.png"] == "https://cdn.example.com/x.png"


async def test_scrub_persisted_presigned_urls(monkeypatch, db_session):
    _install_memory_storage(monkeypatch)
    key = "uploads/2026/01/01/scrub.png"
    presigned = (
        f"https://minio.local/test/{key}"
        "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=deadbeef"
    )
    row = SysFile(
        object_name=key,
        original_name="scrub.png",
        storage_provider=StorageProvider.MINIO.value,
        bucket="test",
        content_type="image/png",
        size=1,
        url=presigned,
    )
    db_session.add(row)
    await db_session.commit()

    service = FileService(db_session)
    changed = await service.scrub_persisted_presigned_urls()
    await db_session.commit()
    assert changed == 1
    refreshed = (
        await db_session.execute(select(SysFile).where(SysFile.object_name == key))
    ).scalar_one()
    assert refreshed.url == key
