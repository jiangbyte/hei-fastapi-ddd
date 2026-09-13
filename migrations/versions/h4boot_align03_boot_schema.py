""" Author: Charlie

对齐 hei-boot 表结构：sys_job/sys_job_log 列名、审计扩展列、profile.name 删除、实名/工作台表。
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h4boot_align03"
down_revision: Union[str, Sequence[str], None] = "g1b2c3sto02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return {c["name"] for c in insp.get_columns(table)}


def _rename_if_exists(table: str, old: str, new: str) -> None:
    cols = _columns(table)
    if old in cols and new not in cols:
        op.alter_column(table, old, new_column_name=new)


def upgrade() -> None:
    if "sys_job" in sa.inspect(op.get_bind()).get_table_names():
        _rename_if_exists("sys_job", "job_name", "name")
        _rename_if_exists("sys_job", "execute_class", "handler")
        _rename_if_exists("sys_job", "execute_type", "trigger_type")
        _rename_if_exists("sys_job", "execute_param", "params")
        _rename_if_exists("sys_job", "last_execute_result", "last_result")

    if "sys_job_log" in sa.inspect(op.get_bind()).get_table_names():
        _rename_if_exists("sys_job_log", "execute_param", "params")
        _rename_if_exists("sys_job_log", "execute_time", "started_at")
        _rename_if_exists("sys_job_log", "execute_duration_ms", "duration_ms")
        _rename_if_exists("sys_job_log", "execute_result", "result")
        log_cols = _columns("sys_job_log")
        if "job_name" in log_cols:
            op.drop_column("sys_job_log", "job_name")

    audit_cols = _columns("sys_operation_audit_log") if "sys_operation_audit_log" in sa.inspect(
        op.get_bind()
    ).get_table_names() else set()
    if audit_cols:
        if "operator_name" not in audit_cols:
            op.add_column(
                "sys_operation_audit_log",
                sa.Column("operator_name", sa.String(128), nullable=True),
            )
        if "action_name" not in audit_cols:
            op.add_column(
                "sys_operation_audit_log",
                sa.Column("action_name", sa.String(128), nullable=True),
            )
        if "action_type" not in audit_cols:
            op.add_column(
                "sys_operation_audit_log",
                sa.Column("action_type", sa.String(32), nullable=True),
            )
        if "module_label" not in audit_cols:
            op.add_column(
                "sys_operation_audit_log",
                sa.Column("module_label", sa.String(128), nullable=True),
            )
        if "duration_ms" not in audit_cols:
            op.add_column(
                "sys_operation_audit_log",
                sa.Column("duration_ms", sa.Integer(), nullable=True),
            )

    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        conn.execute(sa.text("ALTER TABLE profile_user_admin DROP COLUMN IF EXISTS name"))
        conn.execute(sa.text("ALTER TABLE profile_user_portal DROP COLUMN IF EXISTS name"))
    else:
        for table in ("profile_user_admin", "profile_user_portal"):
            if table in sa.inspect(conn).get_table_names() and "name" in _columns(table):
                op.drop_column(table, "name")

    # identity + workspace tables (IF NOT EXISTS, from hei-boot migration)
    if dialect == "postgresql":
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS profile_identity (
                    account_id VARCHAR(64) NOT NULL PRIMARY KEY,
                    status VARCHAR(32) NOT NULL DEFAULT 'UNVERIFIED',
                    document_type VARCHAR(32),
                    real_name_cipher TEXT,
                    document_no_cipher TEXT,
                    document_no_hash VARCHAR(128),
                    verify_channel VARCHAR(32),
                    provider VARCHAR(32),
                    provider_order_no VARCHAR(128),
                    verified_at TIMESTAMPTZ,
                    source_case_id VARCHAR(64),
                    revoked_at TIMESTAMPTZ,
                    revoked_by VARCHAR(64),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    created_by VARCHAR(64),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_by VARCHAR(64)
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uk_profile_identity_document_hash
                ON profile_identity (document_no_hash) WHERE document_no_hash IS NOT NULL
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS real_name_case (
                    case_id VARCHAR(64) NOT NULL PRIMARY KEY,
                    business_type VARCHAR(64) NOT NULL,
                    verify_channel VARCHAR(32) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    account_id VARCHAR(64),
                    target_account_hint_cipher TEXT,
                    applicant_contact_cipher TEXT,
                    document_type VARCHAR(32),
                    real_name_cipher TEXT,
                    document_no_cipher TEXT,
                    document_no_hash VARCHAR(128),
                    attachment_ids TEXT,
                    payload_cipher TEXT,
                    handler_dept_id VARCHAR(64),
                    provider VARCHAR(32),
                    provider_order_no VARCHAR(128),
                    submitter_id VARCHAR(64),
                    reviewer_id VARCHAR(64),
                    reviewed_at TIMESTAMPTZ,
                    reject_reason VARCHAR(512),
                    expire_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    created_by VARCHAR(64),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_by VARCHAR(64)
                )
                """
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS idx_real_name_case_account ON real_name_case (account_id)"
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS idx_real_name_case_status ON real_name_case (business_type, status)"
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS real_name_case_record (
                    record_id VARCHAR(64) NOT NULL PRIMARY KEY,
                    case_id VARCHAR(64) NOT NULL,
                    account_id VARCHAR(64),
                    business_type VARCHAR(64) NOT NULL,
                    action VARCHAR(32) NOT NULL,
                    status_before VARCHAR(32),
                    status_after VARCHAR(32),
                    verify_channel VARCHAR(32),
                    provider VARCHAR(32),
                    operator_id VARCHAR(64),
                    dept_id VARCHAR(64),
                    remark VARCHAR(512),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS idx_real_name_case_record_case ON real_name_case_record (case_id)"
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS sys_workspace_shortcut (
                    id VARCHAR(64) NOT NULL PRIMARY KEY,
                    account_id VARCHAR(64) NOT NULL,
                    resource_id VARCHAR(64) NOT NULL,
                    sort INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    created_by VARCHAR(64),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_by VARCHAR(64),
                    CONSTRAINT uq_sys_workspace_shortcut_account_resource UNIQUE (account_id, resource_id)
                )
                """
            )
        )
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_sys_workspace_shortcut_account_sort "
                "ON sys_workspace_shortcut (account_id, sort)"
            )
        )


def downgrade() -> None:
    # 对齐迁移不做回滚（共用 boot 库结构）。
    pass
