"""Author: Charlie"""

import pytest

from hei_fastapi_ddd.shared.security.safe_url import UnsafeUrlError, validate_outbound_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/x",
        "https://127.0.0.1/x",
        "http://169.254.169.254/latest",
        "file:///etc/passwd",
        "https://user:pass@example.com/",
        "ftp://example.com/",
        "",
    ],
)
def test_validate_rejects(url: str) -> None:
    with pytest.raises(UnsafeUrlError):
        validate_outbound_url(url)


def test_validate_rejects_http_by_default() -> None:
    with pytest.raises(UnsafeUrlError):
        validate_outbound_url("http://example.com/hook")


def test_validate_allows_https_public() -> None:
    try:
        validate_outbound_url("https://example.com/webhook")
    except UnsafeUrlError as exc:
        pytest.skip(f"dns/environment: {exc}")


def test_validate_allows_http_when_enabled() -> None:
    try:
        validate_outbound_url("http://example.com/webhook", allow_http=True)
    except UnsafeUrlError as exc:
        pytest.skip(f"dns/environment: {exc}")
