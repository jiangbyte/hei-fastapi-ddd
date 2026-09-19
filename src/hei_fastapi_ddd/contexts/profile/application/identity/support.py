"""Author: Charlie

用户侧实名视图脱敏（对齐 hei-boot IdentityUserViewSupport）。
"""

from hei_fastapi_ddd.contexts.profile.application.identity.dto import (
    IdentityStatusResponse,
    RealNameCaseSummaryResponse,
)


def sanitize_status(source: IdentityStatusResponse | None) -> IdentityStatusResponse | None:
    if source is None:
        return None
    source.verify_channel = None
    source.provider = None
    sanitize_summary(source.pending_case)
    return source


def sanitize_summary(summary: RealNameCaseSummaryResponse | None) -> RealNameCaseSummaryResponse | None:
    if summary is None:
        return None
    summary.verify_channel = None
    summary.real_name_masked = None
    summary.document_no_masked = None
    return summary
