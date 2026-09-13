""" Author: Charlie """

from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id


def test_generate_snowflake_id_returns_unique_strings():
    first = generate_snowflake_id()
    second = generate_snowflake_id()
    assert isinstance(first, str)
    assert isinstance(second, str)
    assert first != second
