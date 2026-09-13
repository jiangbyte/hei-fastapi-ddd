""" Author: Charlie """

from hei_fastapi_ddd.shared.audit import context as audit_context
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.contexts.auth.application.auth_application_service import _audit_record


def test_audit_record_merges_context_and_explicit_kwargs():
    """显式 resource_id 应覆盖快照上下文（单次 ** 展开，无重复关键字）。"""
    audit_snapshots.resource_id("ctx-id")
    audit_snapshots.subject("ctx-subject")
    try:
        merged = _audit_record(
            module="auth",
            action="login",
            resource_type="auth",
            resource_id="explicit-id",
            success=True,
        )
        assert merged["resource_id"] == "explicit-id"
        assert merged["subject"] == "ctx-subject"
        assert merged["module"] == "auth"
        # 模拟真实调用：单次 ** 展开不应抛 duplicate keyword
        def record(**kwargs):  # noqa: ANN001
            return kwargs

        result = record(**merged)
        assert result["resource_id"] == "explicit-id"
    finally:
        audit_context.clear()
