""" Author: Charlie

订阅 on_audit_event 事件，将审计事件持久化到 sys_operation_audit 表。
"""
import logging

from hei_fastapi_ddd.shared.audit.queue import OperationAuditEvent
from hei_fastapi_ddd.shared.persistence.session import get_session_factory
from hei_fastapi_ddd.shared.messaging import subscribe
from hei_fastapi_ddd.contexts.profile.application.utils.profile import get_profile
from hei_fastapi_ddd.contexts.sys.infrastructure.audit_labels import action_name, build_content, is_path_summary
from hei_fastapi_ddd.contexts.sys.application.audit.support import resolve_account_login
logger = logging.getLogger(__name__)


def _build_module(resource_type: str) -> str:
    """由 resourceType 推导 module（对齐 hei-boot AuditServiceImpl.buildModule）。"""
    normalized = (resource_type or "").strip()
    if not normalized:
        return "unknown"
    if normalized == "resources":
        return "resource"
    idx = normalized.find("_")
    return normalized[:idx] if idx > 0 else normalized


async def _resolve_operator_name(account_id: str | None, account_type: str | None) -> str | None:
    """写入时解析操作人昵称（对齐 hei-gin audit.resolveOperatorName）。"""
    if not account_id:
        return None
    try:
        async with get_session_factory()() as session:
            profile = await get_profile(session, account_type or "admin", account_id)
            if profile is not None:
                nickname = str(getattr(profile, "nickname", "") or "").strip()
                if nickname:
                    return nickname
    except Exception:
        logger.debug("resolve operator name failed for %s", account_id, exc_info=True)
    return None


async def _resolve_subject(event: OperationAuditEvent, operator_name: str | None) -> str | None:
    if event.subject and str(event.subject).strip():
        return str(event.subject).strip()
    if event.account_id:
        try:
            async with get_session_factory()() as session:
                login = await resolve_account_login(session, event.account_id)
                if login:
                    return login
        except Exception:
            logger.debug("resolve audit subject failed for %s", event.account_id, exc_info=True)
    return operator_name or event.account_id


async def _persist_audit_event(event: OperationAuditEvent) -> None:
    """将收到的审计事件写入 sys_operation_audit 表。"""
    from hei_fastapi_ddd.contexts.sys.application.audit.audit_application_service import OperationAuditService

    operator_name = await _resolve_operator_name(event.account_id, event.account_type)
    if operator_name is None:
        operator_name = event.operator_name or event.account_id

    subject = await _resolve_subject(event, operator_name)
    action_name_text = action_name(event.resource_type, event.action)
    summary = event.summary
    if is_path_summary(summary) or summary is None:
        summary = build_content(
            event.action,
            event.resource_type,
            action_name_text,
            subject,
            event.success,
            event.before_data,
            event.after_data,
        )

    async with get_session_factory()() as session:
        await OperationAuditService(session).record(
            module=_build_module(event.resource_type),
            resource_type=event.resource_type,
            action=event.action,
            resource_id=event.resource_id,
            summary=summary,
            before_data=event.before_data,
            after_data=event.after_data,
            success=event.success,
            error_message=event.error_message,
            account_id=event.account_id,
            account_type=event.account_type,
            request_id=event.request_id,
            ip=event.ip,
            user_agent=event.user_agent,
            operator_name=operator_name,
            subject=subject,
            duration_ms=event.duration_ms,
        )


def register() -> None:
    """订阅 on_audit_event 事件，触发审计事件持久化。"""
    subscribe("on_audit_event", _persist_audit_event)
