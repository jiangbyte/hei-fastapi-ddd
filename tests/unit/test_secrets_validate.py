""" Author: Charlie

生产 secrets 校验。
"""
import pytest
from cryptography.fernet import Fernet

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.secrets.backend import clear_secrets_backend_cache
from hei_fastapi_ddd.shared.secrets.validate import validate_secrets_config


def test_validate_allows_fernet_in_debug(monkeypatch):
    clear_secrets_backend_cache()
    monkeypatch.setattr(settings.app, "debug", True)
    monkeypatch.setattr(settings.secrets, "backend", "fernet")
    monkeypatch.setattr(settings.app, "config_crypto_key", "")
    validate_secrets_config()


def test_validate_blocks_empty_key_when_not_debug(monkeypatch):
    clear_secrets_backend_cache()
    monkeypatch.setattr(settings.app, "debug", False)
    monkeypatch.setattr(settings.secrets, "backend", "fernet")
    monkeypatch.setattr(settings.secrets, "allow_fernet_in_prod", True)
    monkeypatch.setattr(settings.app, "config_crypto_key", "")
    with pytest.raises(RuntimeError, match="CONFIG_CRYPTO_KEY"):
        validate_secrets_config()


def test_validate_blocks_fernet_when_not_allowed(monkeypatch):
    clear_secrets_backend_cache()
    monkeypatch.setattr(settings.app, "debug", False)
    monkeypatch.setattr(settings.secrets, "backend", "fernet")
    monkeypatch.setattr(settings.secrets, "allow_fernet_in_prod", False)
    monkeypatch.setattr(settings.secrets, "require_vault", False)
    monkeypatch.setattr(settings.app, "config_crypto_key", Fernet.generate_key().decode())
    with pytest.raises(RuntimeError, match="Production Fernet backend blocked"):
        validate_secrets_config()
