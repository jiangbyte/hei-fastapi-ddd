""" Author: Charlie

文件访问 URL / 对象名规范化单测（对齐 hei-boot FileAccessUrls）。
"""

from hei_fastapi_ddd.shared.storage.url import (
    is_external_url,
    looks_like_presigned_url,
    normalize_object_name,
    quote_object_name,
    strip_to_object_key,
    to_object_key,
)


def test_quote_object_name_preserves_slashes():
    assert quote_object_name("uploads/a b.png") == "uploads/a%20b.png"


def test_strip_legacy_proxy_prefix():
    assert strip_to_object_key("api/v1/files/uploads/a.png") == "uploads/a.png"


def test_strip_path_style_bucket_prefix():
    assert strip_to_object_key("mybucket/uploads/a.png") == "uploads/a.png"


def test_normalize_external_passthrough():
    url = "https://cdn.example.com/a.png"
    assert normalize_object_name(url) == url
    assert is_external_url(url)


def test_looks_like_presigned_url():
    assert looks_like_presigned_url(
        "https://minio.local/bucket/key?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=abc"
    )
    assert not looks_like_presigned_url("https://cdn.example.com/a.png")


def test_to_object_key_from_url():
    assert to_object_key("https://127.0.0.1:9000/vms/uploads/a.png") == "uploads/a.png"
