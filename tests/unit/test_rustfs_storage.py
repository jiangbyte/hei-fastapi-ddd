""" Author: Charlie """

from hei_fastapi_ddd.shared.config.enums import StorageProvider
from hei_fastapi_ddd.shared.storage.config import StorageConfig
from hei_fastapi_ddd.shared.storage.engines import (
    FILE_ENGINE_TO_PROVIDER,
    PROVIDER_TO_KEY_PREFIX,
    engine_to_provider,
)
from hei_fastapi_ddd.shared.storage.manager import _build_storage
from hei_fastapi_ddd.shared.storage.s3 import RustFSStorage


def test_rustfs_engine_mapping():
    assert engine_to_provider("RUSTFS") == StorageProvider.RUSTFS
    assert FILE_ENGINE_TO_PROVIDER["RUSTFS"] == StorageProvider.RUSTFS
    assert PROVIDER_TO_KEY_PREFIX[StorageProvider.RUSTFS] == "STORAGE_RUSTFS"


def test_rustfs_storage_uses_path_style_and_default_region():
    config = StorageConfig(
        id="rustfs",
        name="rustfs",
        provider=StorageProvider.RUSTFS,
        bucket="demo",
        endpoint="http://127.0.0.1:9000",
        access_key="ak",
        secret_key="sk",
        region="",
        use_ssl=False,
    )
    storage = _build_storage(config)
    assert isinstance(storage, RustFSStorage)
    assert storage.config.region == "us-east-1"
    # boto3 Config addressing_style
    s3_config = storage.client.meta.config.s3
    assert s3_config.get("addressing_style") == "path"
    assert storage.client.meta.endpoint_url.rstrip("/") == "http://127.0.0.1:9000"
