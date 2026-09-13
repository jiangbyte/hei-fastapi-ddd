""" Author: Charlie

Secrets backend 冒烟测试。
"""
from cryptography.fernet import Fernet

from hei_fastapi_ddd.shared.secrets.backend import FernetEnvBackend, clear_secrets_backend_cache


def test_fernet_env_roundtrip():
    clear_secrets_backend_cache()
    key = Fernet.generate_key().decode()
    backend = FernetEnvBackend(key)
    token = backend.encrypt("hello-secret")
    assert backend.decrypt(token) == "hello-secret"
    assert backend.decrypt("not-valid") is None
