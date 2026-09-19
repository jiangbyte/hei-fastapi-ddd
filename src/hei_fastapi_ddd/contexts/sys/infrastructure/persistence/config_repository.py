"""系统配置仓储实现。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import Select, delete, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.batch import chunked
from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.shared.persistence.models.sys_config import SysConfig
from hei_fastapi_ddd.types.business import ConflictError, NotFoundError


def _row(entity: SysConfig) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class ConfigRepositoryImpl:
    """系统配置仓储实现。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        if await self.get_by_key(str(data["config_key"])) is not None:
            raise ConflictError("Config key already exists")
        entity = SysConfig(**dict(data))
        self.db.add(entity)
        await self.db.flush()
        return _row(entity)

    async def get_by_id(self, config_id: str) -> SysConfig | None:
        return await self.db.get(SysConfig, config_id)

    async def get_required(self, config_id: str) -> dict[str, Any]:
        entity = await self.get_by_id(config_id)
        if entity is None:
            raise NotFoundError("Config not found")
        return _row(entity)

    async def list_by_ids(self, config_ids: list[str]) -> list[dict[str, Any]]:
        unique_ids = list(dict.fromkeys(config_ids))
        if not unique_ids:
            return []
        entities_by_id: dict[str, SysConfig] = {}
        for batch in chunked(unique_ids):
            rows = (
                (await self.db.execute(select(SysConfig).where(SysConfig.id.in_(batch))))
                .scalars()
                .all()
            )
            for entity in rows:
                entities_by_id[entity.id] = entity
        return [
            _row(entities_by_id[config_id])
            for config_id in unique_ids
            if config_id in entities_by_id
        ]

    async def update(self, config_id: str, data: Mapping[str, Any]) -> None:
        entity = await self.get_by_id(config_id)
        if entity is None:
            raise NotFoundError("Config not found")
        duplicate = await self._get_po_by_key(str(data.get("config_key", entity.config_key)))
        if duplicate is not None and duplicate.id != config_id:
            raise ConflictError("Config key already exists")
        for key, value in data.items():
            if key == "id":
                continue
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, config_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(config_ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysConfig).where(SysConfig.id.in_(unique_ids)))

    async def list_by_category(
        self,
        category: str | None = None,
        scope: str | None = None,
    ) -> list[dict[str, Any]]:
        stmt = select(SysConfig).order_by(SysConfig.sort_code.asc())
        if category:
            stmt = stmt.where(SysConfig.category == category)
        if scope:
            stmt = stmt.where(SysConfig.scope == scope)
        items = list((await self.db.execute(stmt)).scalars().all())
        return [_row(item) for item in items]

    async def get_by_key(self, config_key: str) -> dict[str, Any] | None:
        po = await self._get_po_by_key(config_key)
        return _row(po) if po is not None else None

    async def batch_save(self, items: Sequence[Mapping[str, Any]]) -> None:
        if not items:
            return
        keys = [str(item["config_key"]) for item in items]
        stmt = select(SysConfig).where(SysConfig.config_key.in_(keys))
        existing = {row.config_key: row for row in (await self.db.execute(stmt)).scalars().all()}
        for item in items:
            entity = existing.get(str(item["config_key"]))
            data = dict(item)
            if entity is None:
                self.db.add(
                    SysConfig(
                        id=generate_snowflake_id(),
                        config_key=str(item["config_key"]),
                        config_value=item.get("config_value"),
                        category=item.get("category"),
                        remark=item.get("remark"),
                        value_type=item.get("value_type") or "STRING",
                        label=item.get("label"),
                        scope=item.get("scope"),
                        scene=item.get("scene"),
                        is_builtin=bool(item.get("is_builtin"))
                        if item.get("is_builtin") is not None
                        else False,
                    )
                )
                continue
            entity.config_value = item.get("config_value")
            if item.get("category") is not None:
                entity.category = item.get("category")
            if item.get("remark") is not None:
                entity.remark = item.get("remark")
            if item.get("value_type") is not None:
                entity.value_type = str(item.get("value_type"))
            if "label" in data:
                entity.label = item.get("label")
            if "scope" in data:
                entity.scope = item.get("scope")
            if "scene" in data:
                entity.scene = item.get("scene")
            if item.get("is_builtin") is not None:
                entity.is_builtin = bool(item.get("is_builtin"))
        await self.db.flush()

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[SysConfig]] = select(SysConfig)
        count_stmt = select(func.count(SysConfig.id))
        sql_filters = []
        config_key = filters.get("config_key")
        category = filters.get("category")
        if config_key:
            sql_filters.append(ci_like(SysConfig.config_key, str(config_key)))
        if category:
            sql_filters.append(SysConfig.category == category)
        if sql_filters:
            stmt = stmt.where(*sql_filters)
            count_stmt = count_stmt.where(*sql_filters)
        stmt = (
            stmt.order_by(SysConfig.sort_code.asc(), SysConfig.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [_row(item) for item in items], total

    async def _get_po_by_key(self, config_key: str) -> SysConfig | None:
        stmt = select(SysConfig).where(SysConfig.config_key == config_key)
        return (await self.db.execute(stmt)).scalar_one_or_none()
