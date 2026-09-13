""" Author: Charlie """

from hei_fastapi_ddd.shared.web.pagination import PageQuery, build_page


def test_page_query_uses_current_size_offset():
    query = PageQuery(current=2, size=20)

    assert query.offset == 20


def test_build_page_returns_standard_shape():
    query = PageQuery(current=1, size=20)

    page = build_page(query, 1, ["record"])

    assert page.model_dump() == {
        "size": 20,
        "current": 1,
        "total": 1,
        "pages": 1,
        "records": ["record"],
    }
    assert page.model_dump(mode="json") == {
        "size": "20",
        "current": "1",
        "total": "1",
        "pages": "1",
        "records": ["record"],
    }


def test_page_query_accepts_wire_strings():
    query = PageQuery.model_validate({"current": "3", "size": "10"})
    assert query.current == 3
    assert query.size == 10
    assert query.offset == 20
