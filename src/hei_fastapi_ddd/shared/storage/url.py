""" Author: Charlie

文件 URL 工具：对象名编码、规范化与访问 URL 解析（对齐 hei-boot FileAccessUrls）。

可浏览器访问的 URL 请走 ``FileService.resolve_access_url(s)``（按 sys_file.storage_provider）。
本模块仅提供无 DB 的纯函数规范化。
"""

from __future__ import annotations

from urllib.parse import quote, urlparse


def quote_object_name(object_name: str) -> str:
    """对对象名各段做 URL 编码（保留斜杠分隔）。"""
    return "/".join(quote(part) for part in object_name.strip("/").split("/") if part)


def is_external_url(value: str) -> bool:
    """判断字符串是否为外部 URL（http/https/data/blob）。"""
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https", "data", "blob"}


def looks_like_presigned_url(value: str) -> bool:
    """是否疑似预签名 / 临时存储 URL（不可当永久地址透传）。"""
    if not value:
        return False
    lower = value.lower()
    return (
        "x-amz-" in lower
        or "x-oss-" in lower
        or "signature=" in lower
        or "x-goog-signature" in lower
    )


def strip_to_object_key(path_or_key: str | None) -> str | None:
    """从路径或 key 中提取纯 object key（对齐 hei-boot FileAccessUrls.stripToObjectKey）。"""
    if not path_or_key:
        return None
    normalized = path_or_key.replace("\\", "/").lstrip("/")
    if normalized.startswith("api/v1/files/"):
        normalized = normalized[len("api/v1/files/") :]
    slash = normalized.find("/")
    if slash > 0:
        rest = normalized[slash + 1 :]
        if rest.startswith("uploads/"):
            normalized = rest
    return normalized or None


def normalize_object_name(value: str | None) -> str | None:
    """规范化对象名（纯 object key）；外部 URL 原样返回。"""
    if not value:
        return None
    raw_value = str(value).strip()
    if not raw_value:
        return None
    if is_external_url(raw_value):
        return raw_value
    return strip_to_object_key(raw_value)


def to_object_key(value: str | None) -> str | None:
    """把任意形式的对象引用转成纯 object key（用于存储引擎删除/加载）。"""
    if not value:
        return None
    if is_external_url(value):
        try:
            return strip_to_object_key(urlparse(value.strip()).path)
        except Exception:
            return None
    return strip_to_object_key(value)
