""" Author: Charlie

操作审计服务层：统一构造审计载荷并落库，同时上报可观测指标。
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.shared.observability.context import (
    account_id_ctx,
    account_type_ctx,
    client_ip_ctx,
    request_id_ctx,
    user_agent_ctx,
)
from hei_fastapi_ddd.shared.observability.metrics import record_operation_audit
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.shared.schema.base import IdQuery, to_schema, to_schema_list
from hei_fastapi_ddd.shared.security.masking import mask_identifier
from hei_fastapi_ddd.contexts.sys.infrastructure.audit_labels import (
    action_name as audit_action_name,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.audit_labels import (
    action_type as audit_action_type,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.audit_labels import (
    build_content,
    is_path_summary,
    normalize_account_type,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.audit_labels import (
    module_label as audit_module_label,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_repository import OperationAuditRepository
from hei_fastapi_ddd.contexts.sys.interfaces.http.audit_schemas import (
    OperationAuditCreate,
    OperationAuditPageQuery,
    OperationAuditRecord,
)

logger = logging.getLogger(__name__)


class OperationAuditService:
    """操作审计服务，负责审计记录的脱敏、持久化与查询。"""

    def __init__(self, db: AsyncSession) -> None:
        """绑定会话并初始化仓储。"""
        self.db = db
        self.repo = OperationAuditRepository(db)

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
        """构造并写入一条审计日志；参数未显式提供时回退到请求上下文。"""
        resolved_account_type = account_type if account_type is not None else account_type_ctx.get()
        resolved_account_type = normalize_account_type(resolved_account_type)
        label_resource = resource_type or module
        resolved_action_name = action_name or audit_action_name(label_resource, action)
        resolved_action_type = action_type or audit_action_type(action)
        resolved_module_label = module_label or audit_module_label(label_resource)
        narrative_subject = (
            subject
            or operator_name
            or resource_id
            or account_id
            or account_id_ctx.get()
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
        payload = OperationAuditCreate(
            module=module,
            resource_type=resource_type,
            # 对资源 ID 与摘要脱敏后再落库，避免日志泄漏敏感标识。
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
                await self.repo.create(payload)
            record_operation_audit(module, action, success)
        except Exception:
            logger.exception("Failed to write operation audit log")

    async def detail(self, query: IdQuery) -> OperationAuditRecord:
        """按主键查询单条审计日志详情。"""
        return to_schema(OperationAuditRecord, await self.repo.get_required(query.id))

    async def page_admin(self, query: OperationAuditPageQuery) -> PageData[OperationAuditRecord]:
        """后台分页查询审计日志。"""
        items, total = await self.repo.page_admin(query)
        return build_page(
            query,
            total,
            to_schema_list(OperationAuditRecord, items),
        )

    async def my_page(
        self, query: OperationAuditPageQuery, account_id: str
    ) -> PageData[OperationAuditRecord]:
        """当前用户本人审计日志分页。"""
        scoped = OperationAuditPageQuery(
            **{**query.model_dump(), "account_id": account_id}
        )
        return await self.page_admin(scoped)

    async def my_detail(self, audit_id: str, account_id: str) -> OperationAuditRecord:
        """当前用户本人审计详情。"""
        record = await self.detail(IdQuery(id=audit_id))
        if record.account_id != account_id:
            raise NotFoundError("Operation audit log not found")
        return record
