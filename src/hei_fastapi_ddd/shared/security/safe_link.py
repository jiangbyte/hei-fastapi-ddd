"""Author: Charlie

校验面向浏览器的链接（Banner 等），拒绝危险 scheme。
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

_DANGEROUS_SCHEME = re.compile(r"(?i)^\s*(javascript|data|vbscript|blob)\s*:")


class UnsafeLinkError(ValueError):
    """链接未通过安全校验。"""


def validate_banner_link(link_type: str | None, raw_url: str | None) -> None:
    """按 link_type 校验 banner url。"""
    lt = (link_type or "").strip().upper() or "URL"
    u = (raw_url or "").strip()
    if lt == "NONE":
        return
    if lt == "ROUTE":
        if not u:
            raise UnsafeLinkError("route link requires path")
        _validate_relative_path(u)
        return
    if lt == "URL":
        if u:
            validate_public_href(u)
        return
    raise UnsafeLinkError(f"unsupported link_type: {link_type}")


def validate_public_href(raw: str) -> None:
    """允许 http(s) 或相对 / 路径。"""
    u = (raw or "").strip()
    if not u:
        raise UnsafeLinkError("empty url")
    if _DANGEROUS_SCHEME.match(u):
        raise UnsafeLinkError("dangerous url scheme")
    if u.startswith("/"):
        _validate_relative_path(u)
        return
    parsed = urlparse(u)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise UnsafeLinkError(f"scheme not allowed: {parsed.scheme}")
    if not parsed.hostname:
        raise UnsafeLinkError("missing host")


def _validate_relative_path(u: str) -> None:
    if not u.startswith("/"):
        raise UnsafeLinkError("path must start with /")
    if u.startswith("//"):
        raise UnsafeLinkError("protocol-relative url not allowed")
    if _DANGEROUS_SCHEME.match(u):
        raise UnsafeLinkError("dangerous url scheme")
    if any(ch in u for ch in ("\r", "\n", "\x00")):
        raise UnsafeLinkError("invalid path characters")
