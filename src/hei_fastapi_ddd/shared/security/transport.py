""" Author: Charlie

认证传输层安全：图形验证码与一次性 RSA 密码传输密钥。

密码在客户端用公钥加密后经 HTTP 传输，服务端用临时私钥解密，
避免明文密码出现在日志与链路上。
"""

import base64
import html
import secrets
from uuid import uuid4

from captcha.image import ImageCaptcha
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import Field

from hei_fastapi_ddd.shared.redis.keys import captcha_key, password_crypto_key
from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.web.schema import ApiResponse
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.security.password import hash_password_async, verify_password_async


class CaptchaResponse(ApiSchema):
    """图形验证码响应：验证码 ID 与图片内容。"""

    captcha_id: str
    image_base64: str
    image_type: str = "image/svg+xml"


class PasswordKeyResponse(ApiSchema):
    """一次性密码传输密钥响应：密钥 ID 与公钥。"""

    key_id: str
    public_key: str


class CaptchaMixin(ApiSchema):
    """需要携带图形验证码的请求参数。"""

    captcha_id: str = Field(min_length=1, max_length=64)
    captcha_value: str = Field(min_length=1, max_length=16)


class PasswordKeyMixin(ApiSchema):
    """需要携带密码传输密钥 ID 的请求参数。"""

    password_key_id: str = Field(min_length=1, max_length=64)


CaptchaApiResponse = ApiResponse[CaptchaResponse]
PasswordKeyApiResponse = ApiResponse[PasswordKeyResponse]

# 去除易混淆字符（0/O、1/I/L）的验证码字母表。
CAPTCHA_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


async def create_captcha(image_format: str = "svg") -> CaptchaResponse:
    """生成图形验证码，并将明文哈希后写入 Redis。"""
    value = "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(4))
    captcha_id = uuid4().hex
    redis = _required_redis("Redis is required for captcha")
    await redis.setex(
        captcha_key(captcha_id),
        settings.auth.captcha_ttl_seconds,
        await hash_password_async(value.lower()),
    )
    if image_format == "png":
        return CaptchaResponse(
            captcha_id=captcha_id,
            image_base64=_captcha_png_base64(value),
            image_type="image/png",
        )
    return CaptchaResponse(captcha_id=captcha_id, image_base64=_captcha_svg_base64(value))


async def verify_captcha(captcha_id: str, captcha_value: str) -> None:
    """校验并一次性消费验证码（无论对错都删除，防止重放）。"""
    redis = _required_redis("Redis is required for captcha")
    key = captcha_key(captcha_id)
    raw = await redis.get(key)
    await redis.delete(key)
    raw_text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    if not raw_text or not await verify_password_async(captcha_value.strip().lower(), str(raw_text)):
        raise BusinessError("Invalid or expired captcha")


async def create_password_key() -> PasswordKeyResponse:
    """生成一次性 RSA 密钥对，私钥存入 Redis，公钥下发给客户端。"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_id = uuid4().hex
    redis = _required_redis("Redis is required for password encryption")
    await redis.setex(
        password_crypto_key(key_id),
        settings.auth.password_crypto_key_ttl_seconds,
        private_pem,
    )
    return PasswordKeyResponse(
        key_id=key_id,
        public_key=base64.b64encode(public_der).decode("ascii"),
    )


async def decrypt_passwords(
    password_key_id: str,
    *encrypted_values: str | None,
) -> list[str | None]:
    """用一次性私钥批量解密传输层加密的密码，解密后即删除私钥。"""
    redis = _required_redis("Redis is required for password encryption")
    key = password_crypto_key(password_key_id)
    raw = await redis.get(key)
    raw_text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    if not raw_text:
        raise BusinessError("Invalid or expired password encryption key")
    try:
        private_key = serialization.load_pem_private_key(
            str(raw_text).encode("utf-8"),
            password=None,
        )
        result: list[str | None] = []
        for value in encrypted_values:
            result.append(_decrypt_password(private_key, value) if value else None)
        return result
    finally:
        await redis.delete(key)


async def decrypt_password(password_key_id: str, encrypted_value: str | None) -> str:
    """解密单个传输层加密密码（缺失时返回空字符串）。"""
    return (await decrypt_passwords(password_key_id, encrypted_value))[0] or ""


def _decrypt_password(private_key, encrypted_value: str) -> str:
    """用 RSA-OAEP 解密单个密文，失败转为统一业务错误。"""
    try:
        ciphertext = base64.b64decode(encrypted_value)
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plaintext.decode("utf-8")
    except Exception as exc:
        raise BusinessError("Invalid encrypted password") from exc


def _captcha_svg_base64(value: str) -> str:
    """渲染带噪点与随机旋转的 SVG 验证码并编码为 base64。"""
    escaped = html.escape(value)
    noise = "\n".join(
        f'<line x1="{secrets.randbelow(140)}" y1="{secrets.randbelow(44)}" '
        f'x2="{secrets.randbelow(140)}" y2="{secrets.randbelow(44)}" '
        f'stroke="#94a3b8" stroke-width="1" opacity="0.45" />'
        for _ in range(6)
    )
    text_nodes = "\n".join(
        f'<text x="{22 + index * 26}" y="{29 + secrets.randbelow(5)}" '
        f'font-size="24" font-family="Arial, sans-serif" font-weight="700" '
        f'fill="#0f172a" transform="rotate({secrets.randbelow(21) - 10} {22 + index * 26} 25)">'
        f"{html.escape(char)}</text>"
        for index, char in enumerate(escaped)
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="140" height="44" '
        'viewBox="0 0 140 44">'
        '<rect width="140" height="44" rx="6" fill="#f8fafc"/>'
        f"{noise}{text_nodes}"
        "</svg>"
    )
    return base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _captcha_png_base64(value: str) -> str:
    """用 Pillow（pip captcha 库）渲染 PNG 验证码并编码为 base64，供不支持 SVG 的小程序端使用。"""
    stream = ImageCaptcha(width=140, height=44).generate(value)
    return base64.b64encode(stream.getvalue()).decode("ascii")


def _required_redis(message: str):
    """获取 Redis 客户端，未初始化时抛出统一业务错误。"""
    redis = get_redis()
    if redis is None:
        raise BusinessError(message)
    return redis
