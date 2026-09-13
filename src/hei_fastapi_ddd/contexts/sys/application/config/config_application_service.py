""" Author: Charlie

系统配置服务层：配置维护、敏感值加解密、同步发布与批量保存。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.config_repository import (
    ConfigRepository,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.config_schemas import (
    CategoryQuery,
    ConfigAdminPageQuery,
    ConfigBatchSaveRequest,
    ConfigCreateRequest,
    ConfigUpdateRequest,
    SysConfigSchema,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.crypto import (
    decrypt_config_value,
    encrypt_config_value,
    is_sensitive,
)
from hei_fastapi_ddd.shared.config.sync import reload_and_publish
from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, to_schema, to_schema_list
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page


class ConfigService:
    """系统配置服务，负责管理端配置维护。"""

    def __init__(self, db: AsyncSession):
        """绑定会话并初始化仓储。"""
        self.db = db
        self.repo = ConfigRepository(db)

    async def _commit_and_reload(self, reason: str) -> None:
        """提交当前请求事务后再重载配置，避免 savepoint 写入对外部会话不可见。"""
        await self.db.commit()
        await reload_and_publish(reason)

    async def create(self, payload: ConfigCreateRequest) -> None:
        """加密敏感值后创建配置并重新加载发布。"""
        payload.config_value = encrypt_config_value(payload.config_key, payload.config_value)
        async with transactional(self.db):
            await self.repo.create(payload)
            entity = await self.repo.get_by_key(payload.config_key)
            if entity is not None:
                audit_snapshots.created_entity(entity)
        await self._commit_and_reload("sys_config.create")

    async def update(self, payload: ConfigUpdateRequest) -> None:
        """校验内置配置约束，加密敏感值后更新并重新加载发布。"""
        entity = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(entity)
        if entity.is_builtin and payload.scene and payload.scene != entity.scene:
            raise BusinessError("内置配置不可修改场景编码")
        if entity.is_builtin:
            payload.is_builtin = True
            payload.scene = entity.scene
            payload.scope = entity.scope or payload.scope
        payload.config_value = encrypt_config_value(payload.config_key, payload.config_value)
        async with transactional(self.db):
            await self.repo.update(payload)
            await self.db.refresh(entity)
            audit_snapshots.after_entity(entity)
        await self._commit_and_reload("sys_config.update")

    async def delete(self, payload: IdsRequest) -> None:
        """拒绝删除内置配置，删除后重新加载发布。"""
        async with transactional(self.db):
            unique_ids = list(dict.fromkeys(payload.ids))
            entities = await self.repo.list_by_ids(unique_ids)
            builtin = [e.config_key for e in entities if e.is_builtin]
            if builtin:
                raise BusinessError(f"内置配置不可删除: {', '.join(builtin)}")
            audit_snapshots.deleted_all(entities)
            await self.repo.delete_many(unique_ids)
        await self._commit_and_reload("sys_config.delete")

    async def detail(self, query: IdQuery) -> SysConfigSchema:
        """查询配置详情；敏感值不回显明文，仅标记 is_set。"""
        entity = await self.repo.get_required(query.id)
        schema = to_schema(SysConfigSchema, entity)
        plain = decrypt_config_value(schema.config_key, entity.config_value) or ""
        if is_sensitive(schema.config_key):
            schema.config_value = ""
            if entity.config_value:
                schema.ext_json = {**(schema.ext_json or {}), "is_set": True}
        else:
            schema.config_value = plain
        return schema

    async def list_by_category(self, query: CategoryQuery) -> list[SysConfigSchema]:
        """按分类/作用域查询，敏感值不回显。"""
        items = await self.repo.list_by_category(query.category)
        schemas = to_schema_list(SysConfigSchema, items)
        for entity, s in zip(items, schemas, strict=True):
            plain = decrypt_config_value(s.config_key, entity.config_value) or ""
            if is_sensitive(s.config_key):
                s.config_value = ""
                if entity.config_value:
                    s.ext_json = {**(s.ext_json or {}), "is_set": True}
            else:
                s.config_value = plain
        return schemas

    async def batch_save(self, payload: ConfigBatchSaveRequest) -> None:
        """批量保存配置，敏感值传空表示保留原值。"""
        items_to_save = []
        for item in payload.items:
            if is_sensitive(item.config_key):
                if not item.config_value:
                    continue  # 密码字段传空表示不修改，保留 DB 原值
                item.config_value = encrypt_config_value(item.config_key, item.config_value)
            items_to_save.append(item)
        if not items_to_save:
            return
        first_key = items_to_save[0].config_key
        before_entity = await self.repo.get_by_key(first_key)
        async with transactional(self.db):
            await self.repo.batch_save(items_to_save)
            after_entity = await self.repo.get_by_key(first_key)
            if before_entity is not None and after_entity is not None:
                audit_snapshots.before_entity(before_entity)
                audit_snapshots.after_entity(after_entity)
            elif after_entity is not None:
                audit_snapshots.created_entity(after_entity)
        await self._commit_and_reload("sys_config.batch_save")

    async def page_admin(self, query: ConfigAdminPageQuery) -> PageData[SysConfigSchema]:
        """后台分页查询，敏感值置空。"""
        items, total = await self.repo.page_admin(query)
        schemas = to_schema_list(SysConfigSchema, items)
        for schema in schemas:
            if is_sensitive(schema.config_key):
                schema.config_value = ""
                entity = next(e for e in items if e.id == schema.id)
                if entity.config_value:
                    schema.ext_json = {**(schema.ext_json or {}), "is_set": True}
        return build_page(query, total, schemas)
