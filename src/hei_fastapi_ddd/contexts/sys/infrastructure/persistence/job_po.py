""" Author: Charlie

定时任务模型：sys_job 任务定义 + sys_job_log 执行记录，字段对齐 hei-boot。
"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.base import Base
from hei_fastapi_ddd.shared.persistence.mixins import TimestampMixin


class SysJob(Base, TimestampMixin):
    """定时任务定义表（对齐 hei-boot sys_job）。"""

    __tablename__ = "sys_job"
    __table_args__ = (
        Index("ix_sys_job_enabled_next_run_time", "enabled", "next_run_time"),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="任务名称")
    handler: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="处理器标识（Boot 为 JobHandler 全限定类名，其他栈为注册 key）",
    )
    trigger_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="触发类型：CRON（表达式）/ FIXED（固定间隔）",
    )
    trigger_config: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="触发配置：CRON 表达式或固定间隔秒数",
    )
    params: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="执行参数（JSON）",
    )
    last_run_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="上次执行时间",
    )
    next_run_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="下次执行时间",
    )
    last_result: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="上次执行结果摘要",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="启用状态",
    )
    description: Mapped[str | None] = mapped_column(String(500), comment="任务描述")
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")


class SysJobLog(Base, TimestampMixin):
    """任务执行记录表（对齐 hei-boot sys_job_log）。"""

    __tablename__ = "sys_job_log"
    __table_args__ = (
        Index("ix_sys_job_log_job_id", "job_id"),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_snowflake_id,
        comment="主键",
    )
    job_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="任务 ID")
    params: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="执行参数快照（JSON）",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="执行开始时间",
    )
    duration_ms: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="执行用时（毫秒）",
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="执行结果：是否成功")
    result: Mapped[str | None] = mapped_column(Text, comment="执行结果摘要 / 错误信息")
    executor: Mapped[str | None] = mapped_column(
        String(64),
        comment="执行人（人工触发为账号 id，调度触发为 system）",
    )
    ip: Mapped[str | None] = mapped_column(String(64), comment="执行实例 IP")
    process_id: Mapped[str | None] = mapped_column(String(32), comment="执行实例进程 ID")
    app_dir: Mapped[str | None] = mapped_column(String(500), comment="执行实例程序目录")
