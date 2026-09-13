""" Author: Charlie

存储密钥加密须对 AK/SK 列使用 Fernet。
"""
import pytest
from cryptography.fernet import Fernet

from hei_fastapi_ddd.shared.config import crypto as crypto_mod
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.secrets.backend import clear_secrets_backend_cache


@pytest.fixture()
def fernet_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings.app, "config_crypto_key", key)
    monkeypatch.setattr(settings.secrets, "backend", "fernet")
    clear_secrets_backend_cache()
    yield key
    clear_secrets_backend_cache()


def test_storage_encrypt_decrypt_roundtrip(fernet_key):
    plain = "AKIA_TEST_SECRET"
    enc = crypto_mod.encrypt_storage_value("secret_key", plain)
    assert enc is not None
    assert enc != plain
    assert crypto_mod.decrypt_storage_value("secret_key", enc) == plain


def test_storage_encrypt_requires_crypto_key(monkeypatch):
    clear_secrets_backend_cache()
    monkeypatch.setattr(settings.app, "config_crypto_key", "")
    monkeypatch.setattr(settings.secrets, "backend", "fernet")
    with pytest.raises(RuntimeError, match="config_crypto_key"):
        crypto_mod.encrypt_storage_value("access_key", "plain")
    clear_secrets_backend_cache()


def test_non_sensitive_storage_column_passthrough(fernet_key):
    assert crypto_mod.encrypt_storage_value("bucket", "my-bucket") == "my-bucket"


def test_decrypt_boot_style_unpadded_fernet_token(monkeypatch):
    """hei-boot FernetCodec 写出无 padding 密文；Python 侧须能解开。"""
    from hei_fastapi_ddd.shared.secrets.backend import clear_secrets_backend_cache

    # 与本地种子 / Boot application-local 默认一致
    key = "XV1rJ-UPAbWeYjprihKNS3ZCCHdBuVbIc0WXmYc70ck="
    monkeypatch.setattr(settings.app, "config_crypto_key", key)
    monkeypatch.setattr(settings.secrets, "backend", "fernet")
    clear_secrets_backend_cache()
    try:
        # scripts/db.sql STORAGE_RUSTFS_*（Boot withoutPadding）
        ak = (
            "gAAAAABqeFtjtOr0lzjyRl8TPLDP5be0LWRCOizoe7P6RlqHaxasJvILz2P27Nau"
            "LfjSKM71tWtwpBPZiltAP2aT5Zi5Jzr1lA"
        )
        sk = (
            "gAAAAABqeFtjH6R_u459TAGXEzeQOa9GRHtG_8xkDrnY8hwiZYyxeRtHh0YqhXsuz"
            "fkY3_Nn3OWId3rStJkCQgQUdwfkLtuAyA"
        )
        assert crypto_mod.decrypt_storage_value("access_key", ak) == "admin"
        assert crypto_mod.decrypt_storage_value("secret_key", sk) == "123456789"
    finally:
        clear_secrets_backend_cache()

