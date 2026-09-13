""" Author: Charlie

启动时校验 secrets 后端配置。
"""
from __future__ import annotations

import logging

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.secrets import clear_secrets_backend_cache, get_secrets_backend

logger = logging.getLogger(__name__)


def validate_secrets_config() -> None:
    """生产环境 secrets 配置错误时 fail-closed。"""
    backend = (settings.secrets.backend or "fernet").strip().lower()
    debug = bool(settings.app.debug)
    key = (settings.app.config_crypto_key or "").strip()

    if not debug and not key and backend == "fernet":
        raise RuntimeError("APP__CONFIG_CRYPTO_KEY is required when APP__DEBUG=false")

    if not debug:
        if settings.secrets.require_vault and backend != "vault":
            raise RuntimeError("SECRETS__REQUIRE_VAULT=true requires SECRETS__BACKEND=vault")
        if backend == "fernet" and not settings.secrets.allow_fernet_in_prod:
            raise RuntimeError(
                "Production Fernet backend blocked; set SECRETS__BACKEND=vault "
                "or SECRETS__ALLOW_FERNET_IN_PROD=true"
            )

    if backend == "vault":
        clear_secrets_backend_cache()
        # 探测 Vault 连通性与密钥是否存在（fail-closed）。
        get_secrets_backend().encrypt("hei-secrets-probe")
        logger.info("Secrets backend vault probe OK")
    else:
        logger.info("Secrets backend: %s", backend)
