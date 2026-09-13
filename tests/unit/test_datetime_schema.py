""" Author: Charlie """

from datetime import UTC, datetime, timedelta

from hei_fastapi_ddd.shared.web.schema import ApiResponse
from hei_fastapi_ddd.shared.schema.base import ApiSchema, to_schema
from hei_fastapi_ddd.shared.schema.datetime import format_utc_iso8601


class SampleSchema(ApiSchema):
    created_at: datetime


def test_schema_normalizes_datetime_to_utc():
    value = datetime(2026, 6, 17, 16, 0, 0, tzinfo=UTC) + timedelta(hours=8)
    schema = SampleSchema(created_at=value)
    assert schema.created_at.tzinfo is not None
    assert format_utc_iso8601(schema.created_at).endswith("Z")


def test_schema_accepts_naive_datetime_as_utc():
    """API 入参 / MySQL ORM 的 naive datetime 统一视为 UTC（不拒绝）。"""
    schema = SampleSchema(created_at=datetime(2026, 6, 17, 12, 0, 0))
    assert schema.created_at.tzinfo is UTC
    assert format_utc_iso8601(schema.created_at) == "2026-06-17T12:00:00Z"


class SampleOrm:
    def __init__(self):
        self.created_at = datetime(2026, 6, 17, 12, 0, 0)


def test_to_schema_assumes_orm_naive_datetime_is_utc():
    schema = to_schema(SampleSchema, SampleOrm())

    assert schema.created_at.tzinfo is UTC
    assert format_utc_iso8601(schema.created_at) == "2026-06-17T12:00:00Z"


def test_api_response_serializes_nested_datetime_values():
    payload = ApiResponse(
        data={
            "created_at": datetime(2026, 6, 17, 12, 0, 0, tzinfo=UTC),
            "records": [{"updated_at": datetime(2026, 6, 17, 13, 0, 0, tzinfo=UTC)}],
        }
    ).model_dump(mode="json")

    assert payload["data"]["created_at"] == "2026-06-17T12:00:00Z"
    assert payload["data"]["records"][0]["updated_at"] == "2026-06-17T13:00:00Z"
