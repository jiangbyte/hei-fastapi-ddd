""" Author: Charlie """

from hei_fastapi_ddd.shared.security.password import (
    hash_password,
    hash_password_async,
    verify_password,
    verify_password_async,
)


def test_hash_password_uses_bcrypt() -> None:
    hashed = hash_password("123456789")

    assert hashed.startswith("$2b$")
    assert verify_password("123456789", hashed)
    assert not verify_password("wrong-password", hashed)


async def test_hash_password_async_offloads_bcrypt() -> None:
    hashed = await hash_password_async("123456789")
    assert hashed.startswith("$2b$")
    assert await verify_password_async("123456789", hashed)
    assert not await verify_password_async("wrong-password", hashed)


def test_verify_password_rejects_non_bcrypt_hash() -> None:
    assert not verify_password(
        "123456789",
        "$pbkdf2-sha256$29000$9F4rZWxtTQkBoHROKWUsRQ$gTUk2O4CMqpmvYVGc5e9.SuCERJnkSefgRbjNtJEfpE",
    )
