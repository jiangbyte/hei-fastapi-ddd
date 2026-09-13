""" Author: Charlie

可插拔 secrets 后端（Fernet 环境变量密钥或 Vault 托管 Fernet 密钥）。
"""
from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import hvac
from cryptography.fernet import Fernet

from hei_fastapi_ddd.shared.config.settings import settings


def _normalize_fernet_token(token: str) -> str:
    """补齐 URL-safe Base64 padding，兼容 hei-boot FernetCodec.withoutPadding() 写出的密文。"""
    trimmed = token.strip()
    pad = (-len(trimmed)) % 4
    if pad:
        return trimmed + ("=" * pad)
    return trimmed


class SecretsBackend(Protocol):
    """secrets 后端协议：加密与解密（解密失败返回 None）。"""

    def encrypt(self, plaintext: str) -> str: ...

    def decrypt(self, ciphertext: str) -> str | None: ...


class FernetEnvBackend:
    """基于环境变量密钥的 Fernet 加解密后端。"""

    def __init__(self, key: str) -> None:
        key = (key or "").strip()
        if not key:
            raise RuntimeError("config_crypto_key is not configured")
        self._fernet = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        """加密明文并返回文本。"""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str | None:
        """解密文本，失败返回 None。"""
        try:
            return self._fernet.decrypt(_normalize_fernet_token(ciphertext).encode()).decode()
        except Exception:
            return None


class VaultKvBackend:
    """从 HashiCorp Vault KV v2 加载 Fernet 密钥；不可达时 fail-closed。"""

    def __init__(
        self,
        *,
        addr: str,
        token: str,
        mount: str,
        path: str,
        key_field: str = "fernet_key",
        timeout_seconds: float = 5.0,
    ) -> None:
        self._addr = addr.rstrip("/")
        self._token = token
        self._mount = mount.strip("/")
        self._path = path.strip("/")
        self._key_field = key_field
        self._timeout = timeout_seconds
        self._fernet: Fernet | None = None

    def _ensure_fernet(self) -> Fernet:
        """懒加载地从 Vault KV v2 读取 Fernet 密钥，失败时 fail-closed。"""
        if self._fernet is not None:
            return self._fernet
        try:
            client = hvac.Client(url=self._addr, token=self._token, timeout=self._timeout)
            secret = client.secrets.kv.v2.read_secret_version(
                path=self._path,
                mount_point=self._mount,
            )
            data = (secret.get("data") or {}).get("data") or {}
            key = str(data.get(self._key_field) or "").strip()
        except Exception as exc:  # noqa: BLE001 — fail-closed
            raise RuntimeError(f"Vault secrets backend unavailable: {exc}") from exc
        if not key:
            raise RuntimeError(f"Vault path missing field '{self._key_field}'")
        self._fernet = Fernet(key.encode())
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """加密明文并返回文本。"""
        return self._ensure_fernet().encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str | None:
        """解密文本，失败返回 None。"""
        try:
            return self._ensure_fernet().decrypt(
                _normalize_fernet_token(ciphertext).encode()
            ).decode()
        except Exception:
            return None


@lru_cache(maxsize=1)
def get_secrets_backend() -> SecretsBackend:
    """按配置返回缓存的 secrets 后端实例（Vault 或 Fernet 环境密钥）。"""
    backend = (settings.secrets.backend or "fernet").strip().lower()
    if backend == "vault":
        return VaultKvBackend(
            addr=settings.secrets.vault_addr,
            token=settings.secrets.vault_token,
            mount=settings.secrets.vault_mount,
            path=settings.secrets.vault_path,
            key_field=settings.secrets.vault_key_field,
            timeout_seconds=settings.secrets.vault_timeout_seconds,
        )
    return FernetEnvBackend(settings.app.config_crypto_key)


def clear_secrets_backend_cache() -> None:
    """清除后端缓存（配置变更后调用）。"""
    get_secrets_backend.cache_clear()


def encrypt_plaintext(value: str) -> str:
    """加密明文。"""
    return get_secrets_backend().encrypt(value)


def decrypt_plaintext(value: str) -> str | None:
    """解密密文，失败返回 None。"""
    return get_secrets_backend().decrypt(value)
