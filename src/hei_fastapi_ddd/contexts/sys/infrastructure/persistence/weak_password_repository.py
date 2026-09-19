"""弱密码库仓储实现。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import Select, delete, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.shared.persistence.models.sys_weak_password import SysWeakPassword
from hei_fastapi_ddd.types.business import ConflictError, NotFoundError


def _row(entity: SysWeakPassword) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class WeakPasswordRepositoryImpl:
    """弱密码库仓储实现。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        password = str(data["password"]).strip()
        await self._ensure_unique(password)
        entity = SysWeakPassword(password=password)
        self.db.add(entity)
        await self.db.flush()
        return _row(entity)

    async def get_by_id(self, row_id: str) -> SysWeakPassword | None:
        return await self.db.get(SysWeakPassword, row_id)

    async def get_required(self, row_id: str) -> dict[str, Any]:
        entity = await self.get_by_id(row_id)
        if entity is None:
            raise NotFoundError("Weak password not found")
        return _row(entity)

    async def update(self, row_id: str, data: Mapping[str, Any]) -> None:
        entity = await self.get_by_id(row_id)
        if entity is None:
            raise NotFoundError("Weak password not found")
        password = str(data["password"]).strip()
        await self._ensure_unique(password, exclude_id=row_id)
        entity.password = password
        await self.db.flush()

    async def delete_many(self, row_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(row_ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysWeakPassword).where(SysWeakPassword.id.in_(unique_ids)))

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[SysWeakPassword]] = select(SysWeakPassword)
        count_stmt = select(func.count(SysWeakPassword.id))
        keyword = filters.get("password") or filters.get("keyword")
        if keyword:
            stmt = stmt.where(ci_like(SysWeakPassword.password, str(keyword)))
            count_stmt = count_stmt.where(ci_like(SysWeakPassword.password, str(keyword)))
        stmt = stmt.order_by(SysWeakPassword.id.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [_row(item) for item in items], total

    async def list_all(self, filters: Mapping[str, Any]) -> list[dict[str, Any]]:
        stmt = select(SysWeakPassword).order_by(SysWeakPassword.id.desc())
        keyword = filters.get("password") or filters.get("keyword")
        if keyword:
            stmt = stmt.where(ci_like(SysWeakPassword.password, str(keyword)))
        items = list((await self.db.execute(stmt)).scalars().all())
        return [_row(item) for item in items]

    async def exists_password(self, password: str) -> bool:
        stmt = select(SysWeakPassword.id).where(SysWeakPassword.password == password).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def _ensure_unique(self, password: str, *, exclude_id: str | None = None) -> None:
        stmt = select(SysWeakPassword.id).where(SysWeakPassword.password == password)
        if exclude_id:
            stmt = stmt.where(SysWeakPassword.id != exclude_id)
        if (await self.db.execute(stmt)).scalar_one_or_none() is not None:
            raise ConflictError("Weak password already exists")
