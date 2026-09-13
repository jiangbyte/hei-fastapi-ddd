""" Author: Charlie

系统配置仓储层：封装配置的持久化、按分类/键查询与批量保存。
"""

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.persistence.batch import chunked
from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.shared.persistence.models.sys_config import SysConfig
from hei_fastapi_ddd.shared.exceptions.business import ConflictError, NotFoundError
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.contexts.sys.interfaces.http.config_schemas import (
    ConfigAdminPageQuery,
    ConfigBatchItem,
    ConfigCreateRequest,
    ConfigUpdateRequest,
)


class ConfigRepository:
    """系统配置仓储，负责配置数据持久化和查询。"""

    def __init__(self, db: AsyncSession):
        """绑定数据库会话。"""
        self.db = db

    async def create(self, payload: ConfigCreateRequest) -> None:
        """新增配置并 flush（config_key 唯一预校验，对齐 hei-boot）。"""
        if await self.get_by_key(payload.config_key) is not None:
            raise ConflictError("Config key already exists")
        entity = SysConfig(**payload.model_dump())
        self.db.add(entity)
        await self.db.flush()

    async def get_by_id(self, config_id: str) -> SysConfig | None:
        """按主键查询配置，不存在返回 None。"""
        return await self.db.get(SysConfig, config_id)

    async def get_required(self, config_id: str) -> SysConfig:
        """按主键查询配置，不存在时抛出 NotFoundError。"""
        entity = await self.get_by_id(config_id)
        if entity is None:
            raise NotFoundError("Config not found")
        return entity

    async def list_by_ids(self, config_ids: list[str]) -> list[SysConfig]:
        """按主键分批查询，保持输入顺序（缺失 ID 静默跳过）。"""
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
        return [entities_by_id[config_id] for config_id in unique_ids if config_id in entities_by_id]

    async def update(self, payload: ConfigUpdateRequest) -> None:
        """按主键更新配置字段（排除 id；config_key 唯一预校验）。"""
        entity = await self.get_required(payload.id)
        duplicate = await self.get_by_key(payload.config_key)
        if duplicate is not None and duplicate.id != payload.id:
            raise ConflictError("Config key already exists")
        data = payload.model_dump(exclude={"id"})
        for key, value in data.items():
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, config_ids: list[str]) -> None:
        """批量删除配置（不存在的 ID 静默跳过，对齐 hei-boot 幂等语义）。"""
        unique_ids = list(dict.fromkeys(config_ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysConfig).where(SysConfig.id.in_(unique_ids)))

    async def list_by_category(
        self,
        category: str | None = None,
        scope: str | None = None,
    ) -> list[SysConfig]:
        """按分类与作用域查询配置，按排序码与 ID 排序。"""
        stmt = select(SysConfig).order_by(SysConfig.sort_code.asc())
        if category:
            stmt = stmt.where(SysConfig.category == category)
        if scope:
            stmt = stmt.where(SysConfig.scope == scope)
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_by_key(self, config_key: str) -> SysConfig | None:
        """按 config_key 查询配置，不存在返回 None。"""
        stmt = select(SysConfig).where(SysConfig.config_key == config_key)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def batch_save(self, items: list[ConfigBatchItem]) -> None:
        """按 config_key upsert。"""
        if not items:
            return
        keys = [item.config_key for item in items]
        stmt = select(SysConfig).where(SysConfig.config_key.in_(keys))
        existing = {
            row.config_key: row
            for row in (await self.db.execute(stmt)).scalars().all()
        }
        for item in items:
            entity = existing.get(item.config_key)
            # 只更新请求显式携带的字段，未提供的字段保留原值。
            data = item.model_dump(exclude_unset=True)
            if entity is None:
                self.db.add(
                    SysConfig(
                        id=generate_snowflake_id(),
                        config_key=item.config_key,
                        config_value=item.config_value,
                        category=item.category,
                        remark=item.remark,
                        value_type=item.value_type or "STRING",
                        label=item.label,
                        scope=item.scope,
                        scene=item.scene,
                        is_builtin=bool(item.is_builtin) if item.is_builtin is not None else False,
                    )
                )
                continue
            entity.config_value = item.config_value
            if item.category is not None:
                entity.category = item.category
            if item.remark is not None:
                entity.remark = item.remark
            if item.value_type is not None:
                entity.value_type = item.value_type
            if "label" in data:
                entity.label = item.label
            if "scope" in data:
                entity.scope = item.scope
            if "scene" in data:
                entity.scene = item.scene
            if item.is_builtin is not None:
                entity.is_builtin = bool(item.is_builtin)
        await self.db.flush()

    async def page_admin(self, query: ConfigAdminPageQuery) -> tuple[list[SysConfig], int]:
        """按查询条件后台分页，返回记录列表与总数。"""
        stmt: Select[tuple[SysConfig]] = select(SysConfig)
        count_stmt = select(func.count(SysConfig.id))
        filters = []
        if query.config_key:
            filters.append(ci_like(SysConfig.config_key, query.config_key))
        if query.category:
            filters.append(SysConfig.category == query.category)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysConfig.sort_code.asc(), SysConfig.created_at.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total
