""" Author: Charlie """

from datetime import UTC, datetime

from hei_fastapi_ddd.shared.schema.datetime import format_utc_iso8601


def test_format_utc_iso8601_uses_z_suffix():
    value = datetime(2026, 6, 17, 12, 0, 0, tzinfo=UTC)
    assert format_utc_iso8601(value) == "2026-06-17T12:00:00Z"


def test_format_utc_iso8601_uses_microsecond_precision():
    value = datetime(2026, 6, 17, 12, 0, 0, 123456, tzinfo=UTC)
    assert format_utc_iso8601(value) == "2026-06-17T12:00:00.123456Z"
