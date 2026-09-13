""" Author: Charlie """

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from hei_fastapi_ddd.contexts.sys.application.job.job_application_service import JobService
from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.schema.base import IdQuery


@pytest.mark.asyncio
async def test_run_now_rejects_disabled_job(monkeypatch):
    service = JobService(db=MagicMock())
    service.repo.get_required = AsyncMock(
        return_value=SimpleNamespace(id="job-1", enabled=False)
    )
    submit = AsyncMock()
    monkeypatch.setattr("hei_fastapi_ddd.contexts.sys.application.job.job_application_service.submit_run", submit)

    with pytest.raises(BusinessError, match="任务未启用"):
        await service.run_now(IdQuery(id="job-1"), executor="admin-1")

    submit.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_now_submits_enabled_job(monkeypatch):
    service = JobService(db=MagicMock())
    service.repo.get_required = AsyncMock(
        return_value=SimpleNamespace(id="job-1", enabled=True)
    )
    submit = AsyncMock()
    monkeypatch.setattr("hei_fastapi_ddd.contexts.sys.application.job.job_application_service.submit_run", submit)

    await service.run_now(IdQuery(id="job-1"), executor="admin-1")

    submit.assert_awaited_once_with("job-1", force=True, executor="admin-1")


def test_ensure_handler_rejects_unknown():
    with pytest.raises(BusinessError, match="未找到任务处理器"):
        JobService._ensure_handler("not_a_real_handler")
