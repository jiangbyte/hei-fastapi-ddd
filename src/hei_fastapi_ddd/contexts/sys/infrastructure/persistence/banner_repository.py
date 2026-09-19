"""展示图仓储实现。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import Select, case, delete, func, inspect, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.banner_po import SysBanner
from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum
from hei_fastapi_ddd.shared.persistence.compat import json_array_contains
from hei_fastapi_ddd.types.business import NotFoundError


def _row(entity: SysBanner) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class BannerRepositoryImpl:
    """展示图仓储实现。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        entity = SysBanner(**dict(data))
        self.db.add(entity)
        await self.db.flush()
        return _row(entity)

    async def _get_po(self, banner_id: str) -> SysBanner | None:
        return await self.db.get(SysBanner, banner_id)

    async def get_by_id(self, banner_id: str) -> dict[str, Any] | None:
        entity = await self._get_po(banner_id)
        return _row(entity) if entity else None

    async def get_required(self, banner_id: str) -> dict[str, Any]:
        entity = await self._get_po(banner_id)
        if entity is None:
            raise NotFoundError("Display image not found")
        return _row(entity)

    async def update(self, banner_id: str, data: Mapping[str, Any]) -> None:
        entity = await self._get_po(banner_id)
        if entity is None:
            raise NotFoundError("Display image not found")
        for key, value in data.items():
            if key == "id":
                continue
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, banner_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(banner_ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysBanner).where(SysBanner.id.in_(unique_ids)))

    async def page_admin(
        self, filters: Mapping[str, Any], *, offset: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[SysBanner]] = select(SysBanner)
        count_stmt = select(func.count(SysBanner.id))
        sql_filters = []
        if filters.get("target_account_type"):
            sql_filters.append(
                json_array_contains(
                    SysBanner.target_account_types, str(filters["target_account_type"])
                )
            )
        for key in ("category", "type", "position", "status"):
            if filters.get(key):
                sql_filters.append(getattr(SysBanner, key) == str(filters[key]))
        if sql_filters:
            stmt = stmt.where(*sql_filters)
            count_stmt = count_stmt.where(*sql_filters)
        stmt = stmt.order_by(SysBanner.sort.asc(), SysBanner.id.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [_row(i) for i in items], total

    async def list_public(
        self,
        *,
        now: datetime,
        filters: Mapping[str, Any],
        account_type: str,
    ) -> list[dict[str, Any]]:
        stmt = select(SysBanner).where(
            json_array_contains(SysBanner.target_account_types, account_type),
            SysBanner.status == StatusEnum.ENABLED.value,
            SysBanner.position == str(filters.get("position")),
            or_(SysBanner.start_at.is_(None), SysBanner.start_at <= now),
            or_(SysBanner.end_at.is_(None), SysBanner.end_at >= now),
        )
        if filters.get("category"):
            stmt = stmt.where(SysBanner.category == str(filters["category"]))
        if filters.get("type"):
            stmt = stmt.where(SysBanner.type == str(filters["type"]))
        stmt = stmt.order_by(SysBanner.sort.asc(), SysBanner.id.desc())
        return [_row(i) for i in (await self.db.execute(stmt)).scalars().all()]

    async def is_public_visible(
        self, banner_id: str, now: datetime, *, account_type: str
    ) -> bool:
        stmt = select(SysBanner.id).where(
            SysBanner.id == banner_id,
            json_array_contains(SysBanner.target_account_types, account_type),
            SysBanner.status == StatusEnum.ENABLED.value,
            or_(SysBanner.start_at.is_(None), SysBanner.start_at <= now),
            or_(SysBanner.end_at.is_(None), SysBanner.end_at >= now),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def increment_interactions(self, deltas: dict[str, int]) -> None:
        positive = {k: v for k, v in deltas.items() if v > 0}
        if not positive:
            return
        await self.db.execute(
            update(SysBanner)
            .where(SysBanner.id.in_(positive))
            .values(
                interaction_count=SysBanner.interaction_count
                + case(positive, value=SysBanner.id, else_=0)
            )
        )

    async def sync_status(self, now: datetime) -> dict[str, int]:
        expired_result = await self.db.execute(
            update(SysBanner)
            .where(
                SysBanner.status == StatusEnum.ENABLED.value,
                SysBanner.end_at.is_not(None),
                SysBanner.end_at < now,
            )
            .values(status=StatusEnum.DISABLED.value, updated_at=now)
        )
        activated_result = await self.db.execute(
            update(SysBanner)
            .where(
                SysBanner.status == StatusEnum.DISABLED.value,
                SysBanner.start_at.is_not(None),
                SysBanner.start_at <= now,
                or_(SysBanner.end_at.is_(None), SysBanner.end_at >= now),
            )
            .values(status=StatusEnum.ENABLED.value, updated_at=now)
        )
        return {
            "expired": int(expired_result.rowcount or 0),
            "activated": int(activated_result.rowcount or 0),
        }
