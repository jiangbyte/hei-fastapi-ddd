"""Author: Charlie

实名敏感字段加解密、哈希与脱敏（Fernet，对齐 hei-boot IdentityCryptoService）。
"""

from __future__ import annotations

import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.secrets.backend import _normalize_fernet_token

logger = logging.getLogger(__name__)


def _resolve_crypto_key() -> str:
    explicit = (settings.profile_identity.crypto_key or "").strip()
    if explicit:
        return explicit
    return (settings.app.config_crypto_key or "").strip()


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet | None:
    key = _resolve_crypto_key()
    if not key:
        logger.warning(
            "profile_identity.crypto_key is empty; identity encryption disabled"
        )
        return None
    try:
        return Fernet(key.encode())
    except Exception as exc:  # noqa: BLE001
        logger.error("Invalid profile_identity.crypto_key: %s", exc)
        return None


def clear_identity_crypto_cache() -> None:
    """配置热更新后清除 Fernet 缓存。"""
    _get_fernet.cache_clear()


def enabled() -> bool:
    return _get_fernet() is not None


def _require_fernet() -> Fernet:
    fernet = _get_fernet()
    if fernet is None:
        raise RuntimeError(
            "Identity crypto is not configured; set PROFILE_IDENTITY__CRYPTO_KEY "
            "or APP__CONFIG_CRYPTO_KEY"
        )
    return fernet


def encrypt(plaintext: str | None) -> str | None:
    if not plaintext or not str(plaintext).strip():
        return None
    return _require_fernet().encrypt(str(plaintext).strip().encode()).decode()


def decrypt(ciphertext: str | None) -> str | None:
    if not ciphertext or not str(ciphertext).strip():
        return None
    plain = _require_fernet().decrypt(
        _normalize_fernet_token(str(ciphertext)).encode()
    ).decode()
    return plain


def hash_document_no(document_type: str | None, document_no: str | None) -> str | None:
    if not document_no or not str(document_no).strip():
        return None
    normalized_type = (document_type or "").strip().upper()
    normalized_no = str(document_no).strip().upper()
    return hashlib.sha256(f"{normalized_type}|{normalized_no}".encode()).hexdigest()


def mask_real_name(real_name: str | None) -> str | None:
    if not real_name or not str(real_name).strip():
        return None
    trimmed = str(real_name).strip()
    if len(trimmed) <= 1:
        return "*"
    return trimmed[0] + ("*" * (len(trimmed) - 1))


def mask_document_no(document_no: str | None) -> str | None:
    if not document_no or not str(document_no).strip():
        return None
    trimmed = str(document_no).strip()
    if len(trimmed) <= 7:
        return "*" * len(trimmed)
    keep_prefix = min(3, len(trimmed))
    keep_suffix = min(4, len(trimmed) - keep_prefix)
    return (
        trimmed[:keep_prefix]
        + ("*" * (len(trimmed) - keep_prefix - keep_suffix))
        + trimmed[len(trimmed) - keep_suffix :]
    )
