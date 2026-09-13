""" Author: Charlie

密钥管理公共入口：对外暴露 secrets 后端的加解密与缓存清理能力。
"""

from hei_fastapi_ddd.shared.secrets.backend import (
    clear_secrets_backend_cache,
    decrypt_plaintext,
    encrypt_plaintext,
    get_secrets_backend,
)

__all__ = [
    "clear_secrets_backend_cache",
    "decrypt_plaintext",
    "encrypt_plaintext",
    "get_secrets_backend",
]
