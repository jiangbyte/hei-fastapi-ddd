""" Author: Charlie

HTTP JSON 的 wire 标量序列化/解析。
"""
from hei_fastapi_ddd.shared.web.pagination import PageQuery, build_page
from hei_fastapi_ddd.shared.web.schema import success
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireBool, parse_wire_bool, parse_wire_int, serialize_wire_value


class SampleSchema(ApiSchema):
    enabled: WireBool = True
    count: int = 0


def test_success_envelope_code_is_string():
    payload = success({"ok": True, "n": 3}).model_dump(mode="json")
    assert payload["code"] == "200"
    assert payload["data"] == {"ok": "true", "n": "3"}


def test_page_meta_is_string():
    query = PageQuery(current="2", size="10")
    page = build_page(query, 25, [SampleSchema(enabled=False, count=1)])
    payload = page.model_dump(mode="json")
    assert payload["current"] == "2"
    assert payload["size"] == "10"
    assert payload["total"] == "25"
    assert payload["pages"] == "3"
    assert payload["records"][0] == {"enabled": "false", "count": "1"}


def test_parse_wire_helpers():
    assert parse_wire_bool("true") is True
    assert parse_wire_bool("0") is False
    assert parse_wire_int("42") == 42
    assert serialize_wire_value({"a": True, "b": [1, False]}) == {"a": "true", "b": ["1", "false"]}
