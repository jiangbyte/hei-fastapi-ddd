""" Author: Charlie

DictAggregate 领域单元测试。
"""

from __future__ import annotations

import pytest

from hei_fastapi_ddd.contexts.sys.domain.dict.aggregate import DictAggregate
from hei_fastapi_ddd.ddd_kernel.domain_exception import DomainException


def test_create_normalizes_and_validates_code() -> None:
    agg = DictAggregate.create(id="1", code="SYS_STATUS", label="状态")
    assert agg.code == "SYS_STATUS"
    assert agg.status == "ENABLED"


def test_create_rejects_invalid_code() -> None:
    with pytest.raises(DomainException):
        DictAggregate.create(id="1", code="bad-code")


def test_update_rejects_self_parent() -> None:
    agg = DictAggregate.create(id="1", code="A")
    with pytest.raises(DomainException):
        agg.update(
            code="A",
            label=None,
            value=None,
            color=None,
            category=None,
            parent_id="1",
            status="ENABLED",
            sort=0,
        )


def test_enable_disable() -> None:
    agg = DictAggregate.create(id="1", code="A")
    agg.disable()
    assert agg.status == "DISABLED"
    agg.enable()
    assert agg.status == "ENABLED"
