"""Unit tests for public site footer resolver."""

from hei_fastapi_ddd.contexts.auth.api.auth_schemas import SiteFooterResponse
from hei_fastapi_ddd.contexts.sys.application.public.site_footer import resolve_site_footer


def test_resolve_site_footer_defaults_empty() -> None:
    footer = SiteFooterResponse.model_validate(resolve_site_footer())
    assert footer.copyright_text == ""
    assert footer.icp_number == ""
