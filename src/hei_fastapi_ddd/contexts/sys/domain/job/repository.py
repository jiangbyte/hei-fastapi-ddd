"""job 仓储端口。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol


class JobRepository(Protocol):
    """定时任务定义仓储。"""

    async def create(self, data: Mapping[str, Any], *, next_run_time: datetime) -> dict[str, Any]:
        ...

    async def get_by_id(self, job_id: str) -> dict[str, Any] | None:
        ...

    async def get_required(self, job_id: str) -> dict[str, Any]:
        ...

    async def update(self, job_id: str, data: Mapping[str, Any]) -> None:
        ...

    async def update_run_state(
        self,
        job_id: str,
        *,
        last_run_time: datetime,
        next_run_time: datetime,
        last_result: str | None,
    ) -> None:
        """任务执行后更新调度状态。"""
        ...

    async def set_next_run_time(self, job_id: str, next_run_time: datetime) -> None:
        ...

    async def delete_many(self, job_ids: list[str]) -> None:
        ...

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        ...

    async def find_due_jobs(self, now: datetime, *, limit: int) -> list[dict[str, Any]]:
        ...


class JobLogRepository(Protocol):
    """任务执行日志仓储。"""

    async def create(self, data: Mapping[str, Any]) -> None:
        ...

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        ...

    async def cleanup_expired(self, *, before: datetime, batch_size: int) -> int:
        ...
