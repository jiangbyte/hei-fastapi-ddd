""" Author: Charlie

跨数据库方言兼容：JSON 数组操作与大小写不敏感 LIKE（PostgreSQL / MySQL）。
"""

from __future__ import annotations

from sqlalchemy import Integer, String, cast, func
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.functions import FunctionElement, GenericFunction


class json_array_length(GenericFunction[int]):  # noqa: N801 — SQLAlchemy 函数名保持小写
    """JSON 数组长度：PG 用 json_array_length，MySQL 用 json_length。"""

    type = Integer()
    inherit_cache = True
    name = "json_array_length"


@compiles(json_array_length, "postgresql")
def _compile_json_array_length_pg(element: FunctionElement, compiler, **kw) -> str:
    arg = compiler.process(element.clauses, **kw)
    return f"json_array_length({arg})"


@compiles(json_array_length, "mysql")
@compiles(json_array_length, "mariadb")
def _compile_json_array_length_mysql(element: FunctionElement, compiler, **kw) -> str:
    arg = compiler.process(element.clauses, **kw)
    return f"json_length({arg})"


def json_array_contains(column: ColumnElement, value: str) -> ColumnElement[bool]:
    """跨方言粗匹配：JSON 数组序列化后包含 `"VALUE"`。"""
    return cast(column, String).contains(f'"{value}"')


def ci_like(column: ColumnElement, value: str) -> ColumnElement[bool]:
    """大小写不敏感模糊包含：自动转义 LIKE 通配符，保证 PG/MySQL 一致。"""
    pattern = f"%{escape_like(value or '')}%"
    return func.lower(column).like(pattern.lower(), escape="\\")


def escape_like(value: str) -> str:
    """转义 LIKE 通配符，使 `_` / `%` / `\\` 按字面匹配。"""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def like_contains(column: ColumnElement, value: str) -> ColumnElement[bool]:
    """模糊包含：转义用户输入中的通配符，避免 `_` 被当成单字符通配。"""
    return column.like(f"%{escape_like(value)}%", escape="\\")


def dialect_name_from_url(url: str) -> str:
    """从 SQLAlchemy URL 解析方言名：postgresql / mysql。"""
    scheme = (url or "").split("://", 1)[0].lower()
    driver = scheme.split("+", 1)[0]
    if driver in {"postgresql", "postgres"}:
        return "postgresql"
    if driver in {"mysql", "mariadb"}:
        return "mysql"
    raise ValueError(f"Unsupported database URL scheme: {scheme!r} (only postgresql/mysql)")
