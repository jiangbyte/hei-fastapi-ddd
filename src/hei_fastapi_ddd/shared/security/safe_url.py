"""Author: Charlie

校验出站 HTTP(S) URL，缓解 SSRF（禁止私网/元数据地址等）。
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata",
    }
)


class UnsafeUrlError(ValueError):
    """出站 URL 未通过 SSRF 校验。"""


def validate_outbound_url(raw_url: str, *, allow_http: bool = False) -> str:
    """校验并返回规范化 URL；失败抛出 UnsafeUrlError。"""
    raw = (raw_url or "").strip()
    if not raw:
        raise UnsafeUrlError("empty url")

    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme == "https":
        pass
    elif scheme == "http":
        if not allow_http:
            raise UnsafeUrlError("http scheme not allowed")
    else:
        raise UnsafeUrlError(f"scheme not allowed: {parsed.scheme}")

    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrlError("url userinfo not allowed")

    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("missing host")

    host_lower = host.lower()
    if host_lower in _BLOCKED_HOSTS:
        raise UnsafeUrlError(f"blocked host: {host}")

    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"dns lookup failed: {host}") from exc

    if not infos:
        raise UnsafeUrlError("dns lookup returned no addresses")

    seen: set[str] = set()
    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        if ip_str in seen:
            continue
        seen.add(ip_str)
        if _is_blocked_ip(ip_str):
            raise UnsafeUrlError(f"blocked address: {ip_str}")

    return raw


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    ):
        return True
    # CGNAT 100.64.0.0/10（部分 Python 版本 is_private 已含；双保险）
    if ip in ipaddress.ip_network("100.64.0.0/10"):
        return True
    return False
