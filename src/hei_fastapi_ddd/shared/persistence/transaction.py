""" Author: Charlie

事务工具：提供可嵌套的事务上下文管理器，安全处理事务提交与回滚。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transactional(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    """事务包装：外层 begin；已在事务中则使用 savepoint，避免嵌套 commit/rollback 误伤外层。"""
    if session.in_transaction():
        async with session.begin_nested():
            yield session
        return
    async with session.begin():
        yield session
