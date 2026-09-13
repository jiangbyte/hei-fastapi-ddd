""" Author: Charlie

文件引擎（DEFAULT_FILE_ENGINE）与 StorageProvider / sys_config 键前缀映射。
"""

from __future__ import annotations

from hei_fastapi_ddd.shared.config.enums import StorageProvider

# DEFAULT_FILE_ENGINE 取值 → provider（仅对象存储，对齐 hei-boot）
FILE_ENGINE_TO_PROVIDER: dict[str, StorageProvider] = {
    "MINIO": StorageProvider.MINIO,
    "RUSTFS": StorageProvider.RUSTFS,
    "ALIYUN": StorageProvider.OSS,
    "TENCENT": StorageProvider.S3,
}

PROVIDER_TO_FILE_ENGINE: dict[str, str] = {
    StorageProvider.MINIO.value: "MINIO",
    StorageProvider.RUSTFS.value: "RUSTFS",
    StorageProvider.OSS.value: "ALIYUN",
    StorageProvider.S3.value: "TENCENT",
}

# provider → sys_config 键前缀（STORAGE_{ENGINE}_*）
PROVIDER_TO_KEY_PREFIX: dict[StorageProvider, str] = {
    StorageProvider.MINIO: "STORAGE_MINIO",
    StorageProvider.RUSTFS: "STORAGE_RUSTFS",
    StorageProvider.OSS: "STORAGE_ALIYUN",
    StorageProvider.S3: "STORAGE_TENCENT",
}

PROVIDER_DISPLAY_NAMES: dict[StorageProvider, str] = {
    StorageProvider.MINIO: "MinIO",
    StorageProvider.RUSTFS: "RustFS",
    StorageProvider.OSS: "阿里云 OSS",
    StorageProvider.S3: "腾讯云 COS",
}


def engine_to_provider(engine: str | None) -> StorageProvider | None:
    """把 DEFAULT_FILE_ENGINE 字符串映射为 StorageProvider。"""
    if not engine:
        return None
    return FILE_ENGINE_TO_PROVIDER.get(str(engine).strip().upper())


def provider_to_engine(provider: StorageProvider | str) -> str | None:
    """把 StorageProvider 反向映射为引擎字符串。"""
    value = provider.value if isinstance(provider, StorageProvider) else str(provider)
    return PROVIDER_TO_FILE_ENGINE.get(value)


def config_key(provider: StorageProvider, field_suffix: str) -> str:
    """拼接某存储提供方的 sys_config 键。"""
    return f"{PROVIDER_TO_KEY_PREFIX[provider]}_{field_suffix}"
