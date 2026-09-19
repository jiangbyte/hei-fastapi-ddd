""" Author: Charlie

登出与当前账号注销。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hei_fastapi_ddd.contexts.auth.application.dto import CancelAccountCommand
from hei_fastapi_ddd.contexts.auth.application.base import _audit_record
from hei_fastapi_ddd.contexts.auth.application.support.account_login import resolve_account_login_label
from hei_fastapi_ddd.contexts.iam.application.account.notify import notify_account_cancel_lifecycle
from hei_fastapi_ddd.contexts.sys.application.audit.audit_application_service import (
    OperationAuditService,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store


class LifecycleMixin:
    """登出与当前账号注销。"""

    async def logout(self, token: str) -> None:
        """注销指定 token 对应的会话。"""
        await session_store.delete(token)
        await OperationAuditService(self.db).record(
            module="auth",
            action="logout",
            resource_type="auth",
            resource_id=token,
            success=True,
        )

    async def cancel_current_account(
        self,
        payload: CancelAccountCommand,
        session: SessionPayload,
    ) -> None:
        """注销当前登录账号，并清理该账号下全部会话。"""
        account_before = await self.account_api.get_required(session.account_id)
        account_name = (
            await resolve_account_login_label(self.account_api, session.account_id)
            or session.account_id
        )
        audit_snapshots.before_entity(account_before)
        audit_snapshots.subject(account_name)
        async with transactional(self.db):
            account = await self.account_api.cancel(
                session.account_id,
                cancelled_by=session.account_id,
                cancel_reason=payload.cancel_reason,
            )
        audit_snapshots.after_entity(account)
        await self.session_service.delete_account_sessions(
            str(account["account_type"]), str(account["id"])
        )
        await OperationAuditService(self.db).record(
            **_audit_record(
                module="auth",
                action="cancel",
                resource_type="auth",
                resource_id=account["id"],
                success=True,
                account_id=account["id"],
                account_type=account["account_type"],
            )
        )
        retention_days = config_reader.get_int("ACCOUNT_CANCEL_RETENTION_DAYS", 15)
        cancelled_at = account["cancelled_at"] or datetime.now(UTC)
        purge_at = (cancelled_at + timedelta(days=retention_days)).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        await notify_account_cancel_lifecycle(
            scene="ACCOUNT_CANCELLED",
            email=account["cancel_notify_email"],
            phone=account["cancel_notify_phone"],
            variables={
                "app_name": settings.app.name,
                "retention_days": str(retention_days),
                "purge_at": purge_at,
            },
        )
