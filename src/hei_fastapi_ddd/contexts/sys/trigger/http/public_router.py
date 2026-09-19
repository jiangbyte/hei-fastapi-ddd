""" Author: Charlie

公开站点信息接口（无需登录）。
"""

from fastapi import APIRouter

from hei_fastapi_ddd.contexts.auth.api.auth_schemas import SiteFooterResponse
from hei_fastapi_ddd.contexts.sys.application.public.site_footer import resolve_site_footer
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

router = APIRouter()


@router.get(
    "/v1/public/site-footer",
    response_model=ApiResponse[SiteFooterResponse],
)
async def site_footer() -> ApiResponse[SiteFooterResponse]:
    """站点页脚：版权与备案信息。"""
    return success(SiteFooterResponse.model_validate(resolve_site_footer()))
