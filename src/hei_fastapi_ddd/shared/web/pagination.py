""" Author: Charlie

标准分页查询参数与响应体，统一页码、总量与每页大小计算。
"""

from math import ceil
from typing import Generic, TypeVar

from pydantic import Field

from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireInt

T = TypeVar("T")


class PageQuery(ApiSchema):
    """分页查询参数：current 从 1 开始，size 上限 100。"""

    current: WireInt = Field(default=1, ge=1)
    size: WireInt = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        """数据库查询偏移量（0 基）。"""
        return (int(self.current) - 1) * int(self.size)


class PageData(ApiSchema, Generic[T]):
    """标准分页响应体，统一返回页码、总量和当前页数据。"""

    size: WireInt
    current: WireInt
    total: WireInt
    pages: WireInt
    records: list[T]


def build_page(query: PageQuery, total: int, items: list[T]) -> PageData[T]:
    """构造统一分页模型，避免各路由重复计算总页数和手工拼装字典。"""
    size = int(query.size)
    current = int(query.current)
    total_i = int(total)
    return PageData(
        size=size,
        current=current,
        total=total_i,
        pages=ceil(total_i / size) if total_i else 0,
        records=items,
    )
