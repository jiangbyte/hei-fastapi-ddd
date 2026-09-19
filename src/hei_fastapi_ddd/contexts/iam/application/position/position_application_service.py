"""Author: Charlie

职位应用服务：依赖 domain 仓储端口，不依赖 infrastructure / api。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.position.dto import (
    PositionCreateCommand,
    PositionPageQuery,
    PositionUpdateCommand,
)
from hei_fastapi_ddd.contexts.iam.domain.position.repository import PositionRepository
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.data_scope import IAM_DEPT_PAGE, IAM_POSITION_PAGE
from hei_fastapi_ddd.shared.security.data_scope import resolve_data_scope_dept_ids
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import AuthorizationError


class PositionService:
    """职位应用服务。"""

    def __init__(self, db: AsyncSession, repo: PositionRepository):
        self.db = db
        self.repo = repo

    async def create(
        self,
        command: PositionCreateCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """创建职位，传入 session 时校验所属部门可见性。"""
        # 1. 数据范围：所属部门须在可见集合内
        if session is not None and command.owner_dept_id:
            await self._ensure_depts_visible(session, "iam:position:create", [command.owner_dept_id])
        # 2. 持久化并写审计
        async with transactional(self.db):
            row = await self.repo.create(command.model_dump())
        audit_snapshots.created_entity(row)

    async def update(
        self,
        command: PositionUpdateCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """更新职位，传入 session 时校验职位与所属部门可见性。"""
        # 1. 可见性校验
        if session is not None:
            await self._ensure_positions_visible(session, "iam:position:update", [command.id])
            if command.owner_dept_id:
                await self._ensure_depts_visible(
                    session, "iam:position:update", [command.owner_dept_id]
                )
        # 2. 审计前快照、更新、审计后快照
        existing = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(command.id, command.model_dump(exclude={"id"}))
            updated = await self.repo.get_required(command.id)
        audit_snapshots.after_entity(updated)

    async def delete(
        self,
        payload: IdsRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """删除职位，传入 session 时先校验可见性。"""
        # 1. 可见性校验
        if session is not None:
            await self._ensure_positions_visible(session, "iam:position:delete", payload.ids)
        # 2. 批量加载审计快照并删除
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = [await self.repo.get_required(entity_id) for entity_id in unique_ids]
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """查询职位详情行。"""
        if session is not None:
            await self._ensure_positions_visible(session, "iam:position:detail", [query.id])
        return await self.repo.get_required(query.id)

    async def page_admin(
        self,
        query: PositionPageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[dict]:
        """分页查询职位，叠加数据范围过滤。"""
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
            session=session,
        )
        return build_page(query, total, items)  # type: ignore[arg-type]

    async def _ensure_positions_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        position_ids: list[str],
    ) -> None:
        """校验目标职位均在当前数据范围内，否则抛授权错误。"""
        unique_ids = list(dict.fromkeys(position_ids))
        if not unique_ids:
            return
        if await self.repo.count_positions_in_scope(
            unique_ids,
            session=session,
            permission=permission_key,
        ) != len(unique_ids):
            raise AuthorizationError("Position is outside current data scope")

    async def _ensure_depts_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        dept_ids: list[str],
    ) -> None:
        """校验目标部门均在当前可见部门集合内，否则抛授权错误。"""
        _ = permission_key
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return
        visible_dept_ids = await resolve_data_scope_dept_ids(self.db, session, IAM_DEPT_PAGE)
        if visible_dept_ids is None:
            return
        allowed_ids = set(visible_dept_ids)
        if any(dept_id not in allowed_ids for dept_id in unique_ids):
            raise AuthorizationError("Dept is outside current data scope")
