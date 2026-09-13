""" Author: Charlie """

import io
import json
import logging

import structlog

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.logger.setup import setup_logging
from hei_fastapi_ddd.shared.observability.context import (
    bind_request_log_context,
    clear_request_log_context,
)


def _configure_json_logging(monkeypatch) -> io.StringIO:
    monkeypatch.setattr(settings.observability, "log_json", True)
    monkeypatch.setattr(settings.observability, "log_dir", "")
    clear_request_log_context()
    setup_logging(force=True)

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    # 复用根 stdout handler 的 ProcessorFormatter。
    root = logging.getLogger()
    handler.setFormatter(root.handlers[0].formatter)
    root.handlers.clear()
    root.addHandler(handler)
    return stream


def _last_json(stream: io.StringIO) -> dict:
    lines = [line for line in stream.getvalue().splitlines() if line.strip()]
    assert lines, "expected log output"
    return json.loads(lines[-1])


def test_structlog_json_access_event(monkeypatch):
    stream = _configure_json_logging(monkeypatch)
    try:
        bind_request_log_context(request_id="rid-1", method="GET", path="/")
        structlog.get_logger("access").info(
            "http.access",
            status_code=200,
            duration_ms=1.5,
            client_ip="127.0.0.1",
        )
        payload = _last_json(stream)
    finally:
        clear_request_log_context()

    assert payload["event"] == "http.access"
    assert payload["request_id"] == "rid-1"
    assert payload["method"] == "GET"
    assert payload["path"] == "/"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 1.5
    assert payload["client_ip"] == "127.0.0.1"
    assert payload["service"] == settings.observability.service_name
    assert payload["environment"] == settings.observability.environment


def test_stdlib_logger_picks_up_structlog_context(monkeypatch):
    stream = _configure_json_logging(monkeypatch)
    try:
        bind_request_log_context(request_id="rid-stdlib")
        logging.getLogger("app.demo").info("hello-stdlib")
        payload = _last_json(stream)
    finally:
        clear_request_log_context()

    assert payload["event"] == "hello-stdlib"
    assert payload["request_id"] == "rid-stdlib"
    assert payload["logger"] == "app.demo"


def test_structlog_omits_empty_fields(monkeypatch):
    stream = _configure_json_logging(monkeypatch)
    clear_request_log_context()
    structlog.get_logger("app.test").info("boot")
    payload = _last_json(stream)

    assert payload["event"] == "boot"
    assert "request_id" not in payload
    assert "method" not in payload
