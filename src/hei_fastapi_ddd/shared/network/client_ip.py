""" Author: Charlie

客户端真实 IP 解析：仅当直连方是可信代理时才采纳 X-Real-IP / X-Forwarded-For，
防止客户端伪造转发头绕过 IP 风控。
"""

from __future__ import annotations

import ipaddress

from starlette.requests import Request

from hei_fastapi_ddd.shared.config.settings import settings


def get_client_ip(request: Request) -> str | None:
    """解析真实客户端 IP；仅信任来自可信代理的转发头。"""
    direct_ip = request.client.host if request.client else None
    if not direct_ip or not _is_trusted_proxy(direct_ip):
        return direct_ip

    real_ip = _first_header_ip(request.headers.get("x-real-ip"))
    if real_ip:
        return real_ip

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return _first_header_ip(forwarded_for) or direct_ip
    return direct_ip


def _first_header_ip(value: str | None) -> str | None:
    """取转发头列表中的首个 IP（最靠近客户端的地址）。"""
    if not value:
        return None
    candidate = value.split(",", 1)[0].strip()
    return candidate or None


def _is_trusted_proxy(remote_ip: str) -> bool:
    """判断直连 IP 是否命中可信代理白名单（支持 *、精确 IP 与 CIDR）。"""
    trusted = settings.app.trusted_proxy_ips
    if not trusted:
        return False
    if "*" in trusted:
        return True
    try:
        remote = ipaddress.ip_address(remote_ip)
    except ValueError:
        return remote_ip in trusted

    for item in trusted:
        try:
            if remote in ipaddress.ip_network(item, strict=False):
                return True
        except ValueError:
            if item == remote_ip:
                return True
    return False
