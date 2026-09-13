""" Author: Charlie

存储配置解析与缓存单测（对象存储）。
"""

from dataclasses import replace

import pytest

from hei_fastapi_ddd.shared.config.enums import StorageProvider
from hei_fastapi_ddd.shared.storage import manager as storage_manager
from hei_fastapi_ddd.shared.storage.config import StorageConfig
from hei_fastapi_ddd.shared.storage.s3 import S3CompatibleStorage


@pytest.fixture(autouse=True)
def clear_storage_manager_cache():
    storage_manager.clear_storage_cache()
    yield
    storage_manager.clear_storage_cache()


def _minio_config(config_id: str, *, is_default: bool = False, bucket_public: bool = True) -> StorageConfig:
    return StorageConfig(
        id=config_id,
        name=config_id,
        provider=StorageProvider.MINIO,
        bucket="test-bucket",
        endpoint="http://127.0.0.1:9000",
        access_key="ak",
        secret_key="sk",
        bucket_public=bucket_public,
        base_url="https://cdn.example.com" if bucket_public else "",
        force_path_style=True,
        is_default=is_default,
    )


def test_resolve_storage_config_uses_snapshot_config_id_and_provider(monkeypatch):
    default_config = _minio_config("minio-default", is_default=True)
    archive_config = _minio_config("minio-archive", bucket_public=True)
    archive_config = replace(archive_config, base_url="https://archive.example.com")
    monkeypatch.setattr(
        storage_manager.config_reader,
        "_storage_configs",
        {
            default_config.id: default_config,
            archive_config.id: archive_config,
        },
    )
    monkeypatch.setattr(storage_manager.config_reader, "_default_storage_id", default_config.id)
    monkeypatch.setattr(storage_manager.config_reader, "_version", 100)

    assert storage_manager.resolve_storage_config("minio-archive") == archive_config
    assert storage_manager.resolve_storage_config(provider=StorageProvider.MINIO) == default_config

    class _FakeStorage:
        def __init__(self, config: StorageConfig) -> None:
            self.config = config

        def get_object_url(self, object_name: str) -> str:
            return f"{self.config.base_url.rstrip('/')}/{object_name}"

    monkeypatch.setattr(storage_manager, "_build_storage", lambda config: _FakeStorage(config))
    storage = storage_manager.get_storage("minio-archive", allow_settings_fallback=False)
    assert storage.get_object_url("a/b.txt") == "https://archive.example.com/a/b.txt"


def test_storage_cache_is_versioned_by_config_snapshot(monkeypatch):
    first_config = _minio_config("minio-default", is_default=True)
    monkeypatch.setattr(
        storage_manager.config_reader,
        "_storage_configs",
        {first_config.id: first_config},
    )
    monkeypatch.setattr(storage_manager.config_reader, "_default_storage_id", first_config.id)
    monkeypatch.setattr(storage_manager.config_reader, "_version", 1)

    builds: list[StorageConfig] = []

    def _build(config: StorageConfig):
        builds.append(config)
        return object()

    monkeypatch.setattr(storage_manager, "_build_storage", _build)
    first_storage = storage_manager.get_storage(allow_settings_fallback=False)

    second_config = replace(first_config, base_url="https://v2.example.com")
    monkeypatch.setattr(
        storage_manager.config_reader,
        "_storage_configs",
        {second_config.id: second_config},
    )
    monkeypatch.setattr(storage_manager.config_reader, "_version", 2)

    second_storage = storage_manager.get_storage(allow_settings_fallback=False)
    assert second_storage is not first_storage
    assert len(builds) == 2


def test_explicit_unknown_storage_config_id_does_not_fallback(monkeypatch):
    monkeypatch.setattr(storage_manager.config_reader, "_storage_configs", {})
    monkeypatch.setattr(storage_manager.config_reader, "_default_storage_id", None)

    with pytest.raises(RuntimeError, match="Storage config is not available"):
        storage_manager.resolve_storage_config("missing-storage")


def test_public_url_uses_base_url_when_bucket_public():
    config = _minio_config("minio", bucket_public=True)
    storage = S3CompatibleStorage.__new__(S3CompatibleStorage)
    storage.config = config
    storage.bucket = config.bucket
    storage.force_path_style = True
    storage._endpoint_url = "http://127.0.0.1:9000"
    assert storage._build_public_direct_url("uploads/a.png") == "https://cdn.example.com/uploads/a.png"


def test_config_value_type_coerced():
    from hei_fastapi_ddd.shared.config.coerce import coerce_config_value

    assert coerce_config_value("false", bool) is False
    assert coerce_config_value("42", int) == 42
    assert coerce_config_value("2.5", float) == 2.5
    assert coerce_config_value('["a", "b"]', list[str]) == ["a", "b"]
    assert coerce_config_value("not-an-int", int) is None
    assert coerce_config_value("true", bool | None) is True
    assert coerce_config_value(None, int) is None
