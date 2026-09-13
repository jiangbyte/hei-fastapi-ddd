""" Author: Charlie

弱密码库仓储层：封装弱密码的持久化、去重校验与查询。
"""

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.shared.persistence.models.sys_weak_password import SysWeakPassword
from hei_fastapi_ddd.shared.exceptions.business import ConflictError, NotFoundError
from hei_fastapi_ddd.contexts.sys.interfaces.http.weak_password_schemas import (
    WeakPasswordAdminPageQuery,
    WeakPasswordCreateRequest,
    WeakPasswordListQuery,
    WeakPasswordUpdateRequest,
)


class WeakPasswordRepository:
    """弱密码库仓储。"""

    def __init__(self, db: AsyncSession):
        """绑定数据库会话。"""
        self.db = db

    async def create(self, payload: WeakPasswordCreateRequest) -> None:
        """校验密码唯一后新增弱密码（密码 trim 存储，对齐 hei-boot）。"""
        password = payload.password.strip()
        await self._ensure_unique(password)
        self.db.add(SysWeakPassword(password=password))
        await self.db.flush()

    async def get_by_id(self, row_id: str) -> SysWeakPassword | None:
        """按主键查询，不存在返回 None。"""
        return await self.db.get(SysWeakPassword, row_id)

    async def get_required(self, row_id: str) -> SysWeakPassword:
        """按主键查询，不存在时抛出 NotFoundError。"""
        entity = await self.get_by_id(row_id)
        if entity is None:
            raise NotFoundError("Weak password not found")
        return entity

    async def update(self, payload: WeakPasswordUpdateRequest) -> None:
        """校验密码唯一后更新弱密码（密码 trim 存储，对齐 hei-boot）。"""
        entity = await self.get_required(payload.id)
        password = payload.password.strip()
        await self._ensure_unique(password, exclude_id=payload.id)
        entity.password = password
        await self.db.flush()

    async def delete_many(self, row_ids: list[str]) -> None:
        """批量删除（不存在的 ID 静默跳过，对齐 hei-boot 幂等语义）。"""
        unique_ids = list(dict.fromkeys(row_ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysWeakPassword).where(SysWeakPassword.id.in_(unique_ids)))

    async def page_admin(
        self, query: WeakPasswordAdminPageQuery
    ) -> tuple[list[SysWeakPassword], int]:
        """按密码模糊匹配后台分页，返回记录列表与总数。"""
        stmt: Select[tuple[SysWeakPassword]] = select(SysWeakPassword)
        count_stmt = select(func.count(SysWeakPassword.id))
        keyword = query.password or query.keyword
        if keyword:
            stmt = stmt.where(ci_like(SysWeakPassword.password, keyword))
            count_stmt = count_stmt.where(ci_like(SysWeakPassword.password, keyword))
        stmt = (
            stmt.order_by(SysWeakPassword.id.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def list_all(self, query: WeakPasswordListQuery) -> list[SysWeakPassword]:
        """按密码模糊匹配列出全部弱密码（keyword 为密码兜底过滤）。"""
        stmt = select(SysWeakPassword).order_by(SysWeakPassword.id.desc())
        keyword = query.password or query.keyword
        if keyword:
            stmt = stmt.where(ci_like(SysWeakPassword.password, keyword))
        return list((await self.db.execute(stmt)).scalars().all())

    async def exists_password(self, password: str) -> bool:
        """判断指定密码是否已存在于弱密码库。"""
        stmt = select(SysWeakPassword.id).where(SysWeakPassword.password == password).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def _ensure_unique(self, password: str, *, exclude_id: str | None = None) -> None:
        """校验密码唯一（排除自身），重复时抛出 ConflictError。"""
        stmt = select(SysWeakPassword.id).where(SysWeakPassword.password == password)
        if exclude_id:
            stmt = stmt.where(SysWeakPassword.id != exclude_id)
        if (await self.db.execute(stmt)).scalar_one_or_none() is not None:
            raise ConflictError("Weak password already exists")
