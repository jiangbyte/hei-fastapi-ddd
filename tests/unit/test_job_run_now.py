""" Author: Charlie """

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from hei_fastapi_ddd.contexts.sys.application.job.job_application_service import JobService
from hei_fastapi_ddd.types.business import BusinessError


def _service() -> JobService:
    return JobService(
        db=MagicMock(),
        repo=MagicMock(),
        log_repo=MagicMock(),
        runner=MagicMock(),
    )


@pytest.mark.asyncio
async def test_run_now_rejects_disabled_job():
    service = _service()
    service.repo.get_required = AsyncMock(return_value={"id": "job-1", "enabled": False})
    service.runner.submit = AsyncMock()

    with pytest.raises(BusinessError, match="任务未启用"):
        await service.run_now("job-1", executor="admin-1")

    service.runner.submit.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_now_submits_enabled_job():
    service = _service()
    service.repo.get_required = AsyncMock(return_value={"id": "job-1", "enabled": True})
    service.runner.submit = AsyncMock()

    await service.run_now("job-1", executor="admin-1")

    service.runner.submit.assert_awaited_once_with("job-1", force=True, executor="admin-1")


def test_ensure_handler_rejects_unknown():
    with pytest.raises(BusinessError, match="未找到任务处理器"):
        JobService._ensure_handler("not_a_real_handler")
