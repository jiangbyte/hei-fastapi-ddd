""" Author: Charlie """

import base64
import io

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.security.transport import (
    create_captcha,
    create_password_key,
    decrypt_passwords,
    verify_captcha,
)


async def test_captcha_returns_base64_and_is_single_use(monkeypatch):
    monkeypatch.setattr("hei_fastapi_ddd.shared.security.transport.secrets.choice", lambda alphabet: "A")
    monkeypatch.setattr("hei_fastapi_ddd.shared.security.transport.secrets.randbelow", lambda maximum: 0)

    captcha = await create_captcha()

    assert captcha.captcha_id
    assert captcha.image_type == "image/svg+xml"
    assert "<svg" in base64.b64decode(captcha.image_base64).decode("utf-8")

    await verify_captcha(captcha.captcha_id, "aaaa")
    with pytest.raises(BusinessError):
        await verify_captcha(captcha.captcha_id, "aaaa")


async def test_captcha_can_return_png_for_mini_program(monkeypatch):
    monkeypatch.setattr("hei_fastapi_ddd.shared.security.transport.secrets.choice", lambda alphabet: "A")

    class FakeImageCaptcha:
        def __init__(self, width: int, height: int) -> None:
            pass

        def generate(self, value: str):
            return io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"fakepng")

    monkeypatch.setattr("hei_fastapi_ddd.shared.security.transport.ImageCaptcha", FakeImageCaptcha)

    captcha = await create_captcha("png")

    assert captcha.captcha_id
    assert captcha.image_type == "image/png"
    assert base64.b64decode(captcha.image_base64).startswith(b"\x89PNG\r\n\x1a\n")

    await verify_captcha(captcha.captcha_id, "aaaa")


async def test_password_key_decrypts_rsa_oaep_ciphertext():
    key = await create_password_key()

    assert "-----BEGIN PUBLIC KEY-----" not in key.public_key
    assert "-----END PUBLIC KEY-----" not in key.public_key

    public_key = serialization.load_der_public_key(base64.b64decode(key.public_key))
    encrypted = public_key.encrypt(
        b"Secret@123456",
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    decrypted = await decrypt_passwords(key.key_id, base64.b64encode(encrypted).decode("ascii"))

    assert decrypted == ["Secret@123456"]
    with pytest.raises(BusinessError):
        await decrypt_passwords(key.key_id, base64.b64encode(encrypted).decode("ascii"))
