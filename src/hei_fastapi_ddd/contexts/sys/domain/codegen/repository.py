""" Author: Charlie

codegen 仓储端口。
"""

from __future__ import annotations

from typing import Protocol

from hei_fastapi_ddd.contexts.sys.domain.codegen.aggregate import CodegenTable


class CodegenTableRepository(Protocol):
    """codegen 仓储协议。"""

    async def find_by_id(self, id: str) -> CodegenTable | None:
        """按主键查找。"""
        ...

    async def save(self, entity: CodegenTable) -> CodegenTable:
        """持久化聚合。"""
        ...

    async def delete_many(self, ids: list[str]) -> None:
        """批量删除。"""
        ...
