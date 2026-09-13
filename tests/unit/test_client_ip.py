""" Author: Charlie """

from starlette.requests import Request

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.network.client_ip import get_client_ip


def test_forwarded_for_is_ignored_without_trusted_proxy():
    old = settings.app.trusted_proxy_ips
    settings.app.trusted_proxy_ips = []
    try:
        request = _request(
            client_ip="10.0.0.10",
            headers=[(b"x-forwarded-for", b"203.0.113.8")],
        )
        assert get_client_ip(request) == "10.0.0.10"
    finally:
        settings.app.trusted_proxy_ips = old


def test_forwarded_for_is_used_from_trusted_proxy():
    old = settings.app.trusted_proxy_ips
    settings.app.trusted_proxy_ips = ["10.0.0.0/24"]
    try:
        request = _request(
            client_ip="10.0.0.10",
            headers=[(b"x-forwarded-for", b"203.0.113.8, 10.0.0.10")],
        )
        assert get_client_ip(request) == "203.0.113.8"
    finally:
        settings.app.trusted_proxy_ips = old


def _request(client_ip: str, headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "client": (client_ip, 12345),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )
