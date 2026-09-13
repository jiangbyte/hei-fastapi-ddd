"""
由 HEI 代码生成器生成。
Author: Charlie
生成时间：2026-08-08 21:09:52
"""

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_activity_po import (
    CgTestActivity,
)
from hei_fastapi_ddd.contexts.biz.interfaces.http.cg_test_activity_schemas import (
    CgTestActivityAdminPageQuery,
    CgTestActivityCreateRequest,
    CgTestActivityUpdateRequest,
)
from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.shared.persistence.batch import chunked
from hei_fastapi_ddd.shared.persistence.compat import ci_like


class CgTestActivityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        payload: CgTestActivityCreateRequest,
        *,
        owner_dept_id: str | None = None,
    ) -> CgTestActivity:
        entity = CgTestActivity(**payload.model_dump())
        if owner_dept_id is not None:
            entity.owner_dept_id = owner_dept_id
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id(self, entity_id: str) -> CgTestActivity | None:
        return await self.db.get(CgTestActivity, entity_id)

    async def get_required(self, entity_id: str) -> CgTestActivity:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError("CgTestActivity not found")
        return entity

    async def update(self, payload: CgTestActivityUpdateRequest) -> None:
        entity = await self.get_required(payload.id)
        for key, value in payload.model_dump(exclude={"id"}).items():
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, entity_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(entity_ids))
        if not unique_ids:
            return
        for batch in chunked(unique_ids):
            stmt = select(CgTestActivity.id).where(CgTestActivity.id.in_(batch))
            existing_ids = set((await self.db.execute(stmt)).scalars().all())
            if len(existing_ids) != len(batch):
                raise NotFoundError('CgTestActivity not found')
            await self.db.execute(delete(CgTestActivity).where(CgTestActivity.id.in_(batch)))

    async def page_admin(
        self,
        query: CgTestActivityAdminPageQuery,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> tuple[list[CgTestActivity], int]:
        stmt: Select[tuple[CgTestActivity]] = select(CgTestActivity)
        count_stmt = select(func.count(CgTestActivity.id))
        filters = []
        if query.code:
            filters.append(ci_like(CgTestActivity.code, query.code))
        if query.name:
            filters.append(ci_like(CgTestActivity.name, query.name))
        if query.category:
            filters.append(ci_like(CgTestActivity.category, query.category))
        if query.type:
            filters.append(ci_like(CgTestActivity.type, query.type))
        if query.status is not None:
            filters.append(CgTestActivity.status == query.status)
        if data_scope_filter is not None:
            filters.append(data_scope_filter)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = stmt.order_by(CgTestActivity.id.desc()).offset(query.offset).limit(query.size)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total
