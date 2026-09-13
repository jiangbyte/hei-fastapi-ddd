""" Author: Charlie

职位应用服务：职位 CRUD、数据范围可见性校验与名称回显。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.position_po import SysPosition
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.position_repository import (
    PositionRepository,
)
from hei_fastapi_ddd.contexts.iam.interfaces.http.position_schemas import (
    PositionAdminPageQuery,
    PositionCreateRequest,
    PositionUpdateRequest,
    SysPositionSchema,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.exceptions.business import AuthorizationError
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, to_schema, to_schema_list
from hei_fastapi_ddd.shared.security.data_scope import (
    IAM_DEPT_PAGE,
    IAM_POSITION_PAGE,
    build_data_scope_filter,
    resolve_data_scope_dept_ids,
)
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page


class PositionService:
    """职位应用服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PositionRepository(db)

    async def create(
        self, payload: PositionCreateRequest, session: SessionPayload | None = None
    ) -> None:
        """创建职位，传入 session 时校验所属部门可见性。"""
        if session is not None and payload.owner_dept_id:
            await self._ensure_depts_visible(
                session, "iam:position:create", [payload.owner_dept_id]
            )
        async with transactional(self.db):
            await self.repo.create(payload)
        stmt = (
            select(SysPosition)
            .where(
                SysPosition.name == payload.name,
                SysPosition.category == payload.category,
                SysPosition.owner_dept_id == payload.owner_dept_id,
            )
            .order_by(SysPosition.created_at.desc())
            .limit(1)
        )
        entity = (await self.db.execute(stmt)).scalar_one()
        audit_snapshots.created_entity(entity)

    async def update(
        self, payload: PositionUpdateRequest, session: SessionPayload | None = None
    ) -> None:
        """更新职位，传入 session 时校验职位与所属部门可见性。"""
        if session is not None:
            await self._ensure_positions_visible(session, "iam:position:update", [payload.id])
            if payload.owner_dept_id:
                await self._ensure_depts_visible(
                    session, "iam:position:update", [payload.owner_dept_id]
                )
        existing = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(payload)
        updated = await self.repo.get_required(payload.id)
        audit_snapshots.after_entity(updated)

    async def delete(self, payload: IdsRequest, session: SessionPayload | None = None) -> None:
        """删除职位，传入 session 时先校验可见性。"""
        if session is not None:
            await self._ensure_positions_visible(session, "iam:position:delete", payload.ids)
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = list(
            (
                await self.db.execute(
                    select(SysPosition).where(SysPosition.id.in_(unique_ids))
                )
            )
            .scalars()
            .all()
        )
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(
        self, query: IdQuery, session: SessionPayload | None = None
    ) -> SysPositionSchema:
        """查询职位详情并回显创建人昵称。"""
        if session is not None:
            await self._ensure_positions_visible(session, "iam:position:detail", [query.id])
        schema = to_schema(SysPositionSchema, await self.repo.get_required(query.id))
        return schema

    async def page_admin(
        self,
        query: PositionAdminPageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[SysPositionSchema]:
        """分页查询职位，叠加数据范围过滤。"""
        data_scope_filter = (
            await self._position_scope_filter(session, "iam:position:page")
            if session is not None
            else None
        )
        items, total = await self.repo.page_admin(query, data_scope_filter)
        schemas = to_schema_list(SysPositionSchema, items)
        return build_page(query, total, schemas)

    async def _position_scope_filter(self, session: SessionPayload, permission_key: str):
        """构造职位数据范围过滤条件。"""
        return await build_data_scope_filter(
            self.db,
            session,
            permission_key,
            owner_column=SysPosition.created_by,
            dept_column=SysPosition.owner_dept_id,
        )

    async def _ensure_positions_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        position_ids: list[str],
    ) -> None:
        """校验目标职位均在当前数据范围内，否则抛授权错误。"""
        _ = permission_key
        unique_ids = list(dict.fromkeys(position_ids))
        if not unique_ids:
            return
        data_scope_filter = await self._position_scope_filter(session, IAM_POSITION_PAGE)
        if await self.repo.count_positions_in_scope(unique_ids, data_scope_filter) != len(
            unique_ids
        ):
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
