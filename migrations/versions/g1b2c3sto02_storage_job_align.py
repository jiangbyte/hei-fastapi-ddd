""" Author: Charlie

Align storage/job seeds with hei-boot: drop LOCAL orphan job, add job-log cleanup,
replace STORAGE_*_PUBLIC_PATH with STORAGE_*_BUCKET_PUBLIC, remove STORAGE_LOCAL_*.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g1b2c3sto02"
down_revision: Union[str, Sequence[str], None] = "f0a1b2job01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BUCKET_PUBLIC_ROWS = [
    ("7264846649644584871", "STORAGE_ALIYUN_BUCKET_PUBLIC", "阿里云桶是否公开", 14),
    ("7362777511165276641", "STORAGE_TENCENT_BUCKET_PUBLIC", "腾讯云桶是否公开", 20),
    ("7525309778220488671", "STORAGE_MINIO_BUCKET_PUBLIC", "MinIO 桶是否公开", 26),
    ("7507807560036605420", "STORAGE_RUSTFS_BUCKET_PUBLIC", "RustFS 桶是否公开", 47),
]


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM sys_job WHERE id = :id OR execute_class = :cls"),
        {"id": "7541000000000000005", "cls": "sys_file_cleanup_local_orphans"},
    )
    existing = conn.execute(
        sa.text("SELECT 1 FROM sys_job WHERE id = :id"),
        {"id": "7541000000000000007"},
    ).first()
    if not existing:
        conn.execute(
            sa.text(
                "INSERT INTO sys_job (id, job_name, execute_class, execute_type, trigger_config, "
                "execute_param, next_run_time, enabled, description, sort) "
                "VALUES (:id, :job_name, :execute_class, :execute_type, :trigger_config, "
                ":execute_param, now(), FALSE, :description, :sort)"
            ),
            {
                "id": "7541000000000000007",
                "job_name": "任务执行日志清理",
                "execute_class": "sys_job_log_cleanup",
                "execute_type": "CRON",
                "trigger_config": "0 30 3 * * *",
                "execute_param": '{"retentionDays": 30, "batchSize": 1000}',
                "description": "按保留天数批量清理过期 sys_job_log",
                "sort": 7,
            },
        )
    conn.execute(sa.text("DELETE FROM sys_config WHERE config_key LIKE 'STORAGE_LOCAL_%'"))
    conn.execute(sa.text("DELETE FROM sys_config WHERE config_key LIKE 'STORAGE_%_PUBLIC_PATH'"))
    for row_id, key, remark, sort_code in _BUCKET_PUBLIC_ROWS:
        exists = conn.execute(
            sa.text("SELECT 1 FROM sys_config WHERE config_key = :key"),
            {"key": key},
        ).first()
        if exists:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO sys_config (id, config_key, config_value, category, remark, sort_code, "
                "value_type, is_builtin, ext_json) "
                "VALUES (:id, :key, 'FALSE', 'STORAGE', :remark, :sort, 'BOOL', FALSE, '{}')"
            ),
            {"id": row_id, "key": key, "remark": remark, "sort": sort_code},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM sys_job WHERE id = :id"),
        {"id": "7541000000000000007"},
    )
    for _, key, _, _ in _BUCKET_PUBLIC_ROWS:
        conn.execute(sa.text("DELETE FROM sys_config WHERE config_key = :key"), {"key": key})
