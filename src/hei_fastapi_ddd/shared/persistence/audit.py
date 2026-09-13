""" Author: Charlie

审计字段注入：在 SQLAlchemy flush 前自动填充 TimestampMixin 的 created_by / updated_by。

从上下文变量读取当前账户 ID，避免在各仓储层手动维护审计人。
"""

from sqlalchemy import event
from sqlalchemy.orm import Session

from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin
from hei_fastapi_ddd.shared.observability.context import account_id_ctx


def _current_account_id() -> str | None:
    """从上下文变量读取当前账户 ID，无则返回 None。"""
    value = account_id_ctx.get()
    return str(value) if value else None


@event.listens_for(Session, "before_flush")
def inject_audit_fields(session: Session, _flush_context, _instances) -> None:
    """flush 前为新增/变更的 TimestampMixin 实体填充审计人。"""
    account_id = _current_account_id()
    if not account_id:
        return

    deleted = set(session.deleted)
    for entity in session.new:
        if isinstance(entity, TimestampMixin):
            if getattr(entity, "created_by", None) is None:
                entity.created_by = account_id
            if getattr(entity, "updated_by", None) is None:
                entity.updated_by = account_id

    for entity in session.dirty:
        if entity in deleted or not isinstance(entity, TimestampMixin):
            continue
        if session.is_modified(entity, include_collections=False):
            entity.updated_by = account_id
