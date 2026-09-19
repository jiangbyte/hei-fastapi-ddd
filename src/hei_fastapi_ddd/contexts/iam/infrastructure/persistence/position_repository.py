"""Author: Charlie

职位仓储实现：实现 domain 端口，不依赖 api Schema。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.position_po import SysPosition
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.mapping_util import mapping_data
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.row_mapper import po_row
from hei_fastapi_ddd.shared.security.data_scope import build_data_scope_filter
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.types.business import NotFoundError


class PositionRepositoryImpl:
    """职位仓储实现。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        data: Mapping[str, Any],
        *,
        owner_dept_id: str | None = None,
    ) -> dict[str, Any]:
        entity = SysPosition(**dict(data))
        if owner_dept_id is not None:
            entity.owner_dept_id = owner_dept_id
        self.db.add(entity)
        await self.db.flush()
        return po_row(entity)

    async def get_by_id(self, position_id: str) -> SysPosition | None:
        return await self.db.get(SysPosition, position_id)

    async def get_required(self, position_id: str) -> dict[str, Any]:
        entity = await self.get_by_id(position_id)
        if entity is None:
            raise NotFoundError("Position not found")
        return po_row(entity)

    async def update(self, position_id: str, data: Mapping[str, Any]) -> None:
        entity = await self.get_by_id(position_id)
        if entity is None:
            raise NotFoundError("Position not found")
        for key, value in data.items():
            if key == "id":
                continue
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, position_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(position_ids))
        if not unique_ids:
            return
        stmt = select(SysPosition.id).where(SysPosition.id.in_(unique_ids))
        existing_ids = set((await self.db.execute(stmt)).scalars().all())
        if len(existing_ids) != len(unique_ids):
            raise NotFoundError("Position not found")
        await self.db.execute(delete(SysPosition).where(SysPosition.id.in_(unique_ids)))

    async def count_positions_in_scope(
        self,
        position_ids: list[str],
        *,
        session: SessionPayload,
        permission: str,
    ) -> int:
        unique_ids = list(dict.fromkeys(position_ids))
        if not unique_ids:
            return 0
        data_scope_filter = await build_data_scope_filter(
            self.db,
            session,
            permission,
            owner_column=SysPosition.created_by,
            dept_column=SysPosition.owner_dept_id,
        )
        stmt = select(func.count(SysPosition.id)).where(
            SysPosition.id.in_(unique_ids),
            data_scope_filter,
        )
        return int((await self.db.execute(stmt)).scalar_one())

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
        session: SessionPayload | None = None,
        permission: str = "iam:position:page",
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[SysPosition]] = select(SysPosition)
        count_stmt = select(func.count(SysPosition.id))
        where: list[Any] = []
        if filters.get("name"):
            where.append(SysPosition.name.contains(filters["name"]))
        if filters.get("category"):
            where.append(SysPosition.category == filters["category"])
        if filters.get("status"):
            where.append(SysPosition.status == filters["status"])
        if session is not None:
            data_scope_filter = await build_data_scope_filter(
                self.db,
                session,
                permission,
                owner_column=SysPosition.created_by,
                dept_column=SysPosition.owner_dept_id,
            )
            if data_scope_filter is not None:
                where.append(data_scope_filter)
        if where:
            stmt = stmt.where(*where)
            count_stmt = count_stmt.where(*where)
        stmt = (
            stmt.order_by(SysPosition.sort.asc(), SysPosition.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [po_row(item) for item in items], int(total)


# 过渡期别名，供尚未切到 wiring 的调用方使用。
PositionRepository = PositionRepositoryImpl
