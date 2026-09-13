""" Author: Charlie

存储配置：定义各存储提供方共用的 StorageConfig 数据类与启动/测试回退配置。
"""

from __future__ import annotations

from dataclasses import dataclass

from hei_fastapi_ddd.shared.config.enums import StorageProvider
from hei_fastapi_ddd.shared.config.settings import settings


@dataclass(frozen=True, slots=True)
class StorageConfig:
    """存储提供方配置：桶、端点、凭据、公开桶与预签名等。"""

    id: str
    name: str
    provider: StorageProvider
    bucket: str = ""
    endpoint: str = ""
    access_key: str = ""
    secret_key: str = ""
    region: str = ""
    use_ssl: bool = False
    base_url: str = ""
    bucket_public: bool = False
    is_default: bool = False
    # MinIO/RustFS 使用 path-style；腾讯云 COS 等默认 virtual-host。
    force_path_style: bool = False
    presign_expire_seconds: int = 3600


def fallback_storage_config() -> StorageConfig:
    """从环境 settings 构建启动/测试回退配置。"""
    provider = StorageProvider(settings.storage.provider)
    force_path_style = provider in {StorageProvider.MINIO, StorageProvider.RUSTFS}
    return StorageConfig(
        id="__settings__",
        name="settings",
        provider=provider,
        bucket=settings.storage.bucket or "",
        endpoint=settings.storage.endpoint or "",
        access_key=settings.storage.access_key or "",
        secret_key=settings.storage.secret_key or "",
        region=settings.storage.region or "",
        use_ssl=settings.storage.use_ssl,
        base_url=settings.storage.base_url or "",
        bucket_public=settings.storage.bucket_public,
        is_default=True,
        force_path_style=force_path_style,
        presign_expire_seconds=settings.storage.presign_expire_seconds,
    )
