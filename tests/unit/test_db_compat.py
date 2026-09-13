""" Author: Charlie

方言兼容辅助单元测试。
"""

from __future__ import annotations

import pytest
from sqlalchemy import String, column, select
from sqlalchemy.dialects import mysql, postgresql

from hei_fastapi_ddd.shared.persistence.compat import (
    ci_like,
    dialect_name_from_url,
    escape_like,
    json_array_contains,
    json_array_length,
    like_contains,
)


def test_dialect_name_from_url() -> None:
    assert dialect_name_from_url("postgresql+asyncpg://u:p@h/db") == "postgresql"
    assert dialect_name_from_url("mysql+aiomysql://u:p@h/db") == "mysql"
    assert dialect_name_from_url("mysql+asyncmy://u:p@h/db") == "mysql"
    with pytest.raises(ValueError):
        dialect_name_from_url("sqlite+aiosqlite:///:memory:")


def test_json_array_length_compiles() -> None:
    col = column("target_account_types")
    stmt = select(json_array_length(col))
    pg_sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}))
    mysql_sql = str(stmt.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": False}))
    assert "json_array_length" in pg_sql.lower()
    assert "json_length" in mysql_sql.lower()


def test_ci_like_and_json_contains_compile() -> None:
    col = column("name", String)
    like_sql = str(
        select(ci_like(col, "AbC")).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "lower" in like_sql.lower()
    assert "%abc%" in like_sql.lower()
    assert "ESCAPE" in like_sql.upper()

    # 用户输入中的通配符会被转义，避免被当成 LIKE 模式。
    escaped_sql = str(
        select(ci_like(col, "%AbC%")).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    ).lower()
    assert "escape" in escaped_sql
    assert "\\\\%" in escaped_sql or r"\%" in escaped_sql

    json_col = column("target_account_types")
    contains_sql = str(
        select(json_array_contains(json_col, "ADMIN")).compile(
            dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert '"ADMIN"' in contains_sql


def test_like_contains_escapes_wildcards() -> None:
    assert escape_like("E2E_DICT_1") == r"E2E\_DICT\_1"
    col = column("code", String)
    sql = str(
        select(like_contains(col, "E2E_ROLE_1")).compile(
            dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert r"E2E\_ROLE\_1" in sql or "E2E\\\\_ROLE\\\\_1" in sql
    assert "ESCAPE" in sql.upper()
