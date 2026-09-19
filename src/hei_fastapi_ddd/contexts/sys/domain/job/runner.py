"""任务执行提交端口。"""

from __future__ import annotations

from typing import Protocol


class JobRunnerPort(Protocol):
    """异步提交任务执行。"""

    async def submit(self, job_id: str, *, force: bool, executor: str) -> None:
        ...
