""" Author: Charlie """

import os

from tests.db_support import resolve_test_db_url


def test_resolve_test_db_url_uses_db_url_by_default(monkeypatch):
    monkeypatch.delenv("TEST_DB__URL", raising=False)
    monkeypatch.setenv(
        "DB__URL",
        "mysql+aiomysql://root:123456@127.0.0.1:3306/hei_fastapi?charset=utf8mb4",
    )
    assert resolve_test_db_url() == os.environ["DB__URL"]


def test_resolve_test_db_url_prefers_explicit_override(monkeypatch):
    monkeypatch.setenv(
        "TEST_DB__URL",
        "mysql+aiomysql://root:123456@127.0.0.1:3306/hei_fastapi_test?charset=utf8mb4",
    )
    assert resolve_test_db_url() == os.environ["TEST_DB__URL"]
