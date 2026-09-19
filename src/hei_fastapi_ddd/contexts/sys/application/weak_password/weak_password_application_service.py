"""弱密码库应用服务。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.weak_password.dto import (
    WeakPasswordAdminPageQuery,
    WeakPasswordCreateCommand,
    WeakPasswordIdsCommand,
    WeakPasswordListQuery,
    WeakPasswordUpdateCommand,
)
from hei_fastapi_ddd.contexts.sys.domain.weak_password.repository import WeakPasswordRepository
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import NotFoundError


class WeakPasswordService:
    """弱密码库用例编排。"""

    def __init__(self, db: AsyncSession, repo: WeakPasswordRepository):
        self.db = db
        self.repo = repo

    async def create(self, command: WeakPasswordCreateCommand) -> None:
        """新增弱密码并写审计。"""
        # 1. trim 密码后持久化
        password = command.password.strip()
        async with transactional(self.db):
            row = await self.repo.create({"password": password})
            audit_snapshots.created_entity(row)

    async def update(self, command: WeakPasswordUpdateCommand) -> None:
        """更新弱密码并写审计。"""
        # 1. 加载前快照
        before = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(before)
        # 2. 事务内更新
        password = command.password.strip()
        async with transactional(self.db):
            await self.repo.update(command.id, {"password": password})
            after = await self.repo.get_required(command.id)
            audit_snapshots.after_entity(after)

    async def delete(self, command: WeakPasswordIdsCommand) -> None:
        """批量删除弱密码。"""
        # 1. 去重并收集已存在行供审计
        unique_ids = list(dict.fromkeys(command.ids))
        rows: list[dict] = []
        for row_id in unique_ids:
            try:
                rows.append(await self.repo.get_required(row_id))
            except NotFoundError:
                continue
        # 2. 写审计并删除
        audit_snapshots.deleted_all(rows)
        await self.repo.delete_many(unique_ids)

    async def detail(self, row_id: str) -> dict:
        """查询详情。"""
        return await self.repo.get_required(row_id)

    async def page_admin(self, query: WeakPasswordAdminPageQuery) -> PageData[dict]:
        """后台分页。"""
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
        )
        return build_page(query, total, items)  # type: ignore[arg-type]

    async def list_all(self, query: WeakPasswordListQuery) -> list[dict]:
        """列表查询。"""
        return await self.repo.list_all(query.model_dump())
