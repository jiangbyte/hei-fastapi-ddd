""" Author: Charlie

配置加密：对敏感配置值（密码、AK/SK 等）做 Fernet/Vault 加密，读回时解密。

非敏感键原样透传，解密失败时按非破坏性策略原样返回明文。
"""

from hei_fastapi_ddd.shared.config.keys import SENSITIVE_CONFIG_KEYS
from hei_fastapi_ddd.shared.secrets import decrypt_plaintext, encrypt_plaintext

# 存储配置中需要加密的敏感列（访问密钥与私钥）。
_storage_sensitive_columns = {
    "access_key",
    "secret_key",
}


def is_sensitive(config_key: str) -> bool:
    """判断配置键是否属于敏感键集合（对齐 hei-boot ConfigServiceImpl.isSensitive）。"""
    if not config_key or not str(config_key).strip():
        return False
    key = str(config_key).strip()
    if key in SENSITIVE_CONFIG_KEYS:
        return True
    return key.startswith("AUTH_OAUTH_") and (
        key.endswith("_CLIENT_SECRET") or key.endswith("_APP_SECRET")
    )


def encrypt_config_value(config_key: str, value: str | None) -> str | None:
    """对敏感键的配置值加密，非敏感或空值原样返回。"""
    if not value or not is_sensitive(config_key):
        return value
    return encrypt_plaintext(value)


def decrypt_config_value(config_key: str, value: str | None) -> str | None:
    """对配置值解密；解密失败时原样返回以兼容明文旧数据。"""
    if not value:
        return value
    decrypted = decrypt_plaintext(value)
    # 明文行或密钥错误：非破坏性读取时原样返回。
    return decrypted if decrypted is not None else value


def is_storage_sensitive(column_name: str) -> bool:
    """判断存储列名是否为敏感列。"""
    return column_name in _storage_sensitive_columns


def encrypt_storage_value(column_name: str, value: str | None) -> str | None:
    """加密存储 AK/SK。需要 secrets 后端（Fernet 环境变量或 Vault）。"""
    if not value or not is_storage_sensitive(column_name):
        return value
    return encrypt_plaintext(value)


def decrypt_storage_value(column_name: str, value: str | None) -> str | None:
    """解密存储敏感列；非敏感列或解密失败时原样返回。"""
    if not value:
        return value
    if not is_storage_sensitive(column_name):
        return value
    decrypted = decrypt_plaintext(value)
    # 轮换前仍为明文行：原样返回。
    return decrypted if decrypted is not None else value

