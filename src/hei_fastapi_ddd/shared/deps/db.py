""" Author: Charlie

数据库依赖：提供请求级异步会话，成功提交、异常回滚。
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.persistence.session import get_session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """请求级 DB 会话：成功提交，异常回滚。

    依赖链里（如 get_current_account）的只读查询会触发 autobegin。
    业务里的 transactional() 在已有事务时只会 begin_nested（savepoint），
    若不在请求结束时 commit，savepoint 变更会随会话关闭一起 rollback。
    """
    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
