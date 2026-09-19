""" Author: Charlie

系统配置应用服务：敏感值加解密、同步发布与批量保存。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.config.dto import (
    CategoryQuery,
    ConfigAdminPageQuery,
    ConfigBatchSaveCommand,
    ConfigCreateCommand,
    ConfigUpdateCommand,
)
from hei_fastapi_ddd.contexts.sys.domain.config.repository import ConfigRepository
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.crypto import (
    decrypt_config_value,
    encrypt_config_value,
    is_sensitive,
)
from hei_fastapi_ddd.shared.config.sync import reload_and_publish
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import BusinessError


class ConfigService:
    """系统配置服务，负责管理端配置维护。"""

    def __init__(self, db: AsyncSession, repo: ConfigRepository):
        self.db = db
        self.repo = repo

    async def _commit_and_reload(self, reason: str) -> None:
        """提交当前请求事务后再重载配置。"""
        await self.db.commit()
        await reload_and_publish(reason)

    async def create(self, command: ConfigCreateCommand) -> None:
        """加密敏感值后创建配置并重新加载发布。"""
        data = command.model_dump()
        data["config_value"] = encrypt_config_value(command.config_key, command.config_value)
        async with transactional(self.db):
            row = await self.repo.create(data)
            audit_snapshots.created_entity(row)
        await self._commit_and_reload("sys_config.create")

    async def update(self, command: ConfigUpdateCommand) -> None:
        """校验内置配置约束，加密敏感值后更新并重新加载发布。"""
        # 1. 加载现有行与审计前快照
        existing = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(existing)
        if existing.get("is_builtin") and command.scene and command.scene != existing.get("scene"):
            raise BusinessError("内置配置不可修改场景编码")
        data = command.model_dump(exclude={"id"})
        if existing.get("is_builtin"):
            data["is_builtin"] = True
            data["scene"] = existing.get("scene")
            data["scope"] = existing.get("scope") or data.get("scope")
        data["config_value"] = encrypt_config_value(command.config_key, command.config_value)
        # 2. 事务内更新并写后快照
        async with transactional(self.db):
            await self.repo.update(command.id, data)
            updated = await self.repo.get_required(command.id)
            audit_snapshots.after_entity(updated)
        await self._commit_and_reload("sys_config.update")

    async def delete(self, ids: list[str]) -> None:
        """拒绝删除内置配置，删除后重新加载发布。"""
        async with transactional(self.db):
            unique_ids = list(dict.fromkeys(ids))
            entities = await self.repo.list_by_ids(unique_ids)
            builtin = [str(e["config_key"]) for e in entities if e.get("is_builtin")]
            if builtin:
                raise BusinessError(f"内置配置不可删除: {', '.join(builtin)}")
            audit_snapshots.deleted_all(entities)
            await self.repo.delete_many(unique_ids)
        await self._commit_and_reload("sys_config.delete")

    async def detail(self, config_id: str) -> dict:
        """查询配置详情；敏感值不回显明文。"""
        entity = await self.repo.get_required(config_id)
        return self._mask_row(entity)

    async def list_by_category(self, query: CategoryQuery) -> list[dict]:
        """按分类查询，敏感值不回显。"""
        items = await self.repo.list_by_category(query.category)
        return [self._mask_row(item) for item in items]

    async def batch_save(self, command: ConfigBatchSaveCommand) -> None:
        """批量保存配置，敏感值传空表示保留原值。"""
        items_to_save: list[dict] = []
        for item in command.items:
            payload = item.model_dump(exclude_unset=True)
            if is_sensitive(item.config_key):
                if not item.config_value:
                    continue
                payload["config_value"] = encrypt_config_value(
                    item.config_key, item.config_value
                )
            items_to_save.append(payload)
        if not items_to_save:
            return
        first_key = str(items_to_save[0]["config_key"])
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

    async def page_admin(self, query: ConfigAdminPageQuery) -> PageData[dict]:
        """后台分页查询，敏感值置空。"""
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
        )
        records = [self._mask_row(item) for item in items]
        return build_page(query, total, records)  # type: ignore[arg-type]

    @staticmethod
    def _mask_row(entity: dict) -> dict:
        """敏感配置脱敏后返回行字典。"""
        row = dict(entity)
        config_key = str(row.get("config_key") or "")
        stored_value = row.get("config_value")
        plain = decrypt_config_value(config_key, stored_value) or ""
        if is_sensitive(config_key):
            row["config_value"] = ""
            if stored_value:
                ext = dict(row.get("ext_json") or {})
                ext["is_set"] = True
                row["ext_json"] = ext
        else:
            row["config_value"] = plain
        return row
