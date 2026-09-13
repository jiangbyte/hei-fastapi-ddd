"""Unit tests for public site footer resolver."""

from hei_fastapi_ddd.contexts.sys.application.public.site_footer import resolve_site_footer


def test_resolve_site_footer_defaults_empty() -> None:
    footer = resolve_site_footer()
    assert footer.copyright_text == ""
    assert footer.icp_number == ""
