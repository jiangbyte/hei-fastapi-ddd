""" Author: Charlie

DDD 内核导出：实体、值对象、仓储协议、领域事件与异常。
"""

from hei_fastapi_ddd.ddd_kernel.domain_event import DomainEvent
from hei_fastapi_ddd.ddd_kernel.domain_exception import DomainException
from hei_fastapi_ddd.ddd_kernel.entity import AggregateRoot, Entity
from hei_fastapi_ddd.ddd_kernel.identifier import Identifier
from hei_fastapi_ddd.ddd_kernel.repository import Repository
from hei_fastapi_ddd.ddd_kernel.value_object import ValueObject

__all__ = [
    "AggregateRoot",
    "DomainEvent",
    "DomainException",
    "Entity",
    "Identifier",
    "Repository",
    "ValueObject",
]
