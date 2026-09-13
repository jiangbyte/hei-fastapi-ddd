""" Author: Charlie

内置任务调度：sys_job / sys_job_log 表 + 预置 6 条任务（对齐 hei-boot db.sql）。

任务 ID 沿用 hei-boot 7541000000000000001~6；execute_class 为 Python 处理器标识。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f0a1b2job01"
down_revision: str | Sequence[str] | None = "a1b2c3oauth01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------ sys_job
    op.create_table(
        "sys_job",
        sa.Column("id", sa.String(length=64), nullable=False, comment="主键"),
        sa.Column("job_name", sa.String(length=128), nullable=False, comment="任务名称"),
        sa.Column(
            "execute_class",
            sa.String(length=255),
            nullable=False,
            comment="任务处理器标识（JobHandler 注册 key）",
        ),
        sa.Column(
            "execute_type",
            sa.String(length=16),
            nullable=False,
            comment="触发类型：CRON 表达式 / FIXED 固定间隔",
        ),
        sa.Column(
            "trigger_config",
            sa.String(length=255),
            nullable=False,
            comment="触发配置：CRON 表达式或固定间隔秒数",
        ),
        sa.Column("execute_param", sa.JSON(), nullable=True, comment="执行参数（JSON 对象）"),
        sa.Column(
            "last_run_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="上次执行时间",
        ),
        sa.Column(
            "next_run_time",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="下次执行时间",
        ),
        sa.Column(
            "last_execute_result",
            sa.String(length=500),
            nullable=True,
            comment="上次执行结果摘要",
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, comment="启用状态"),
        sa.Column("description", sa.String(length=500), nullable=True, comment="任务描述"),
        sa.Column("sort", sa.Integer(), nullable=False, comment="排序"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column("created_by", sa.String(length=64), nullable=True, comment="创建人"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("updated_by", sa.String(length=64), nullable=True, comment="更新人"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_job")),
    )
    op.create_index(
        "ix_sys_job_enabled_next_run_time",
        "sys_job",
        ["enabled", "next_run_time"],
        unique=False,
    )

    # ---------------------------------------------------------------- sys_job_log
    op.create_table(
        "sys_job_log",
        sa.Column("id", sa.String(length=64), nullable=False, comment="主键"),
        sa.Column("job_id", sa.String(length=64), nullable=False, comment="任务 ID"),
        sa.Column(
            "job_name",
            sa.String(length=128),
            nullable=False,
            comment="任务名称（冗余便于展示）",
        ),
        sa.Column("execute_param", sa.JSON(), nullable=True, comment="执行参数快照（JSON）"),
        sa.Column(
            "execute_time",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="执行开始时间",
        ),
        sa.Column(
            "execute_duration_ms",
            sa.BigInteger(),
            nullable=True,
            comment="执行用时（毫秒）",
        ),
        sa.Column("success", sa.Boolean(), nullable=False, comment="执行结果：是否成功"),
        sa.Column("execute_result", sa.Text(), nullable=True, comment="执行结果摘要 / 错误信息"),
        sa.Column(
            "executor",
            sa.String(length=64),
            nullable=True,
            comment="执行人（人工触发为账号 id，调度触发为 system）",
        ),
        sa.Column("ip", sa.String(length=64), nullable=True, comment="执行实例 IP"),
        sa.Column("process_id", sa.String(length=32), nullable=True, comment="执行实例进程 ID"),
        sa.Column("app_dir", sa.String(length=500), nullable=True, comment="执行实例程序目录"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column("created_by", sa.String(length=64), nullable=True, comment="创建人"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("updated_by", sa.String(length=64), nullable=True, comment="更新人"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_job_log")),
    )
    op.create_index("ix_sys_job_log_job_id", "sys_job_log", ["job_id"], unique=False)

    # ------------------------------------------------------------------ 任务种子
    _seed_jobs(op)


def downgrade() -> None:
    op.drop_index("ix_sys_job_log_job_id", table_name="sys_job_log")
    op.drop_table("sys_job_log")
    op.drop_index("ix_sys_job_enabled_next_run_time", table_name="sys_job")
    op.drop_table("sys_job")
    # 任务种子随表删除，无需额外清理。


def _seed_jobs(op) -> None:
    """预置 6 条任务（ID 对齐 hei-boot db.sql），按 id 幂等插入。"""
    conn = op.get_bind()
    rows = [
        {
            "id": "7541000000000000001",
            "job_name": "示例任务",
            "execute_class": "sys_job_sample",
            "execute_type": "FIXED",
            "trigger_config": "60",
            "execute_param": "{}",
            "description": "演示调度链路：回显执行参数",
            "sort": 1,
        },
        {
            "id": "7541000000000000002",
            "job_name": "Banner 状态同步",
            "execute_class": "sys_banner_status_sync",
            "execute_type": "FIXED",
            "trigger_config": "60",
            "execute_param": "{}",
            "description": "按 start_at / end_at 激活或过期 Banner",
            "sort": 2,
        },
        {
            "id": "7541000000000000003",
            "job_name": "Banner 互动计数刷库",
            "execute_class": "sys_banner_flush_interactions",
            "execute_type": "FIXED",
            "trigger_config": "60",
            "execute_param": "{}",
            "description": "将 Redis 互动增量写入 sys_banner.interaction_count",
            "sort": 3,
        },
        {
            "id": "7541000000000000004",
            "job_name": "审计告警",
            "execute_class": "sys_audit_alert",
            "execute_type": "FIXED",
            "trigger_config": "300",
            "execute_param": "{}",
            "description": "按配置规则扫描审计日志并发送告警",
            "sort": 4,
        },
        {
            "id": "7541000000000000006",
            "job_name": "注销账号清理",
            "execute_class": "iam_account_purge_cancelled",
            "execute_type": "CRON",
            "trigger_config": "0 0 3 * * *",
            "execute_param": '{"retentionDays": 15}',
            "description": "每日清理已取消且超过保留期的账号数据",
            "sort": 6,
        },
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
    ]
    for row in rows:
        existing = conn.execute(
            sa.text("SELECT 1 FROM sys_job WHERE id = :id"), {"id": row["id"]}
        ).first()
        if existing:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO sys_job (id, job_name, execute_class, execute_type, trigger_config, "
                "execute_param, next_run_time, enabled, description, sort) "
                "VALUES (:id, :job_name, :execute_class, :execute_type, :trigger_config, "
                ":execute_param, now(), TRUE, :description, :sort)"
            ),
            row,
        )
