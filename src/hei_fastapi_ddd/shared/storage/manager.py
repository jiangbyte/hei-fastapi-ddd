""" Author: Charlie

存储管理器：按配置解析并缓存存储客户端，供仓储层获取对应引擎实例。
"""

from threading import RLock

from hei_fastapi_ddd.shared.config.enums import StorageProvider
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.storage.config import StorageConfig, fallback_storage_config
from hei_fastapi_ddd.shared.storage.oss import OSSStorage
from hei_fastapi_ddd.shared.storage.s3 import MinioStorage, RustFSStorage, S3CompatibleStorage

# (配置版本, StorageConfig) → 存储客户端实例 的进程级缓存。
_storage_cache: dict[tuple[int, StorageConfig], object] = {}
_storage_cache_lock = RLock()


def clear_storage_cache() -> None:
    """清空存储客户端缓存（配置重载后调用）。"""
    with _storage_cache_lock:
        _storage_cache.clear()


def get_storage(
    config_id: str | None = None,
    *,
    provider: StorageProvider | str | None = None,
    allow_settings_fallback: bool = True,
):
    """返回缓存 DB 存储配置对应的存储客户端。"""
    config = resolve_storage_config(
        config_id=config_id,
        provider=provider,
        allow_settings_fallback=allow_settings_fallback,
    )
    cache_key = (config_reader.version, config)
    with _storage_cache_lock:
        storage = _storage_cache.get(cache_key)
        if storage is None:
            storage = _build_storage(config)
            _storage_cache[cache_key] = storage
        return storage


def resolve_storage_config(
    config_id: str | None = None,
    *,
    provider: StorageProvider | str | None = None,
    allow_settings_fallback: bool = True,
) -> StorageConfig:
    """解析目标存储配置：优先 DB 配置，缺失时按 settings 回退。"""
    config: StorageConfig | None = None
    explicit_config_id = bool(config_id) and config_id != "__settings__"
    if config_id:
        config = config_reader.get_storage_config(config_id)
        if config is None:
            try:
                provider = StorageProvider(config_id)
                explicit_config_id = False
            except ValueError:
                pass
    if config is None and provider is not None:
        config = config_reader.get_storage_config_by_provider(StorageProvider(provider))
    if config is None and config_id is None and provider is None:
        config = config_reader.get_default_storage()
    if config is None and allow_settings_fallback and not explicit_config_id:
        config = fallback_storage_config()
    if config is None:
        raise RuntimeError("Storage config is not available")
    return config


def _build_storage(config: StorageConfig):
    """按配置的 provider 构建对应的存储客户端实例。"""
    if config.provider == StorageProvider.MINIO:
        return MinioStorage(config)
    if config.provider == StorageProvider.RUSTFS:
        return RustFSStorage(config)
    if config.provider == StorageProvider.S3:
        return S3CompatibleStorage(config)
    if config.provider == StorageProvider.OSS:
        return OSSStorage(config)
    raise ValueError(f"Unsupported storage provider: {config.provider}")
