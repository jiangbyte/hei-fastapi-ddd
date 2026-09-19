"""操作审计应用服务。"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.audit.dto import (
    OperationAuditCreateCommand,
    OperationAuditPageQuery,
)
from hei_fastapi_ddd.contexts.sys.application.audit.labels import (
    action_name as audit_action_name,
)
from hei_fastapi_ddd.contexts.sys.application.audit.labels import (
    action_type as audit_action_type,
)
from hei_fastapi_ddd.contexts.sys.application.audit.labels import (
    build_content,
    is_path_summary,
    normalize_account_type,
)
from hei_fastapi_ddd.contexts.sys.application.audit.labels import (
    module_label as audit_module_label,
)
from hei_fastapi_ddd.contexts.sys.domain.audit.repository import OperationAuditRepository
from hei_fastapi_ddd.shared.observability.context import (
    account_id_ctx,
    account_type_ctx,
    client_ip_ctx,
    request_id_ctx,
    user_agent_ctx,
)
from hei_fastapi_ddd.shared.observability.metrics import record_operation_audit
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.security.masking import mask_identifier
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import NotFoundError

logger = logging.getLogger(__name__)


class OperationAuditService:
    """操作审计服务。"""

    def __init__(self, db: AsyncSession, repo: OperationAuditRepository) -> None:
        self.db = db
        self.repo = repo

    async def record(
        self,
        *,
        module: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        summary: str | None = None,
        before_data: dict | None = None,
        after_data: dict | None = None,
        success: bool = True,
        error_message: str | None = None,
        account_id: str | None = None,
        account_type: str | None = None,
        request_id: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        operator_name: str | None = None,
        subject: str | None = None,
        action_name: str | None = None,
        action_type: str | None = None,
        module_label: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """构造并写入一条审计日志。"""
        resolved_account_type = account_type if account_type is not None else account_type_ctx.get()
        resolved_account_type = normalize_account_type(resolved_account_type)
        label_resource = resource_type or module
        resolved_action_name = action_name or audit_action_name(label_resource, action)
        resolved_action_type = action_type or audit_action_type(action)
        resolved_module_label = module_label or audit_module_label(label_resource)
        narrative_subject = (
            subject or operator_name or resource_id or account_id or account_id_ctx.get()
        )
        resolved_summary = summary
        if is_path_summary(resolved_summary):
            resolved_summary = None
        if resolved_summary is None:
            resolved_summary = build_content(
                action=action,
                resource_type=label_resource,
                action_name_text=resolved_action_name,
                subject=narrative_subject,
                success=success,
                before_data=before_data,
                after_data=after_data,
            )
        command = OperationAuditCreateCommand(
            module=module,
            resource_type=resource_type,
            resource_id=mask_identifier(resource_id) if resource_id else None,
            action=action,
            summary=mask_identifier(resolved_summary) if resolved_summary else None,
            before_data=before_data,
            after_data=after_data,
            account_id=account_id if account_id is not None else account_id_ctx.get(),
            account_type=resolved_account_type,
            request_id=request_id if request_id is not None else request_id_ctx.get(),
            ip=ip if ip is not None else client_ip_ctx.get(),
            user_agent=user_agent if user_agent is not None else user_agent_ctx.get(),
            success=success,
            error_message=error_message,
            operator_name=operator_name,
            action_name=resolved_action_name,
            action_type=resolved_action_type,
            module_label=resolved_module_label,
            duration_ms=duration_ms,
        )
        try:
            async with transactional(self.db):
                await self.repo.create(command.model_dump())
            record_operation_audit(module, action, success)
        except Exception:
            logger.exception("Failed to write operation audit log")

    async def detail(self, audit_id: str) -> dict:
        return await self.repo.get_required(audit_id)

    async def page_admin(self, query: OperationAuditPageQuery) -> PageData[dict]:
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
        )
        return build_page(query, total, items)  # type: ignore[arg-type]

    async def my_page(self, query: OperationAuditPageQuery, account_id: str) -> PageData[dict]:
        scoped = OperationAuditPageQuery.model_validate(
            {**query.model_dump(), "account_id": account_id}
        )
        return await self.page_admin(scoped)

    async def my_detail(self, audit_id: str, account_id: str) -> dict:
        record = await self.detail(audit_id)
        if record.get("account_id") != account_id:
            raise NotFoundError("Operation audit log not found")
        return record
