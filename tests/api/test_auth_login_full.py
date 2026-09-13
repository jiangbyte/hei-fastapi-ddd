""" Author: Charlie

完整管理端登录路径：captcha + RSA 密码密钥 + cookie。
"""
from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import (
    SysAccount,
    SysAccountIdentity,
)
from hei_fastapi_ddd.factory import create_app
from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.redis.keys import captcha_key
from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.shared.security.password import hash_password
from hei_fastapi_ddd.shared.security.transport import create_captcha, create_password_key


def _encrypt_password(public_key_b64: str, password: str) -> str:
    der = base64.b64decode(public_key_b64)
    public_key = serialization.load_der_public_key(der)
    ciphertext = public_key.encrypt(
        password.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(ciphertext).decode("ascii")


@pytest.mark.asyncio
async def test_admin_login_full_crypto_cookie(fake_redis, db_session: AsyncSession, monkeypatch):
    monkeypatch.setattr(settings.auth, "session_cookie_enabled", True)
    monkeypatch.setattr(settings.auth, "session_cookie_name", "Authorization")
    monkeypatch.setattr(settings.swagger, "enabled", False)

    account = SysAccount(
        password_hash=hash_password("Admin@123456"),
        account_type=AccountType.ADMIN.value,
        account_status=AccountStatusEnum.ENABLED.value,
    )
    db_session.add(account)
    await db_session.flush()
    db_session.add(
        SysAccountIdentity(
            account_id=account.id,
            identity_type=AccountIdentityType.ACCOUNT.value,
            identifier="admin_crypto",
            verified=True,
            is_primary=True,
        )
    )
    await db_session.commit()

    captcha = await create_captcha("svg")
    # 通过重写 redis hash 为已知值恢复 captcha 明文。
    redis = get_redis()
    assert redis is not None
    await redis.setex(captcha_key(captcha.captcha_id), 60, hash_password("ab12"))

    key = await create_password_key()
    encrypted = _encrypt_password(key.public_key, "Admin@123456")

    app = create_app()

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_db

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=True),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/admin/login",
            json={
                "account": "admin_crypto",
                "password": encrypted,
                "identity_type": "ACCOUNT",
                "remember_me": True,
                "password_key_id": key.key_id,
                "captcha_id": captcha.captcha_id,
                "captcha_value": "ab12",
            },
        )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["account_id"] == account.id
    assert response.cookies.get("Authorization")
    assert data["token"]
