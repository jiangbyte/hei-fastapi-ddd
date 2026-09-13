""" Author: Charlie

展示图仓储层：封装展示图持久化、后台分页与公开可见性查询。
"""

from datetime import datetime

from sqlalchemy import Select, case, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum
from hei_fastapi_ddd.shared.persistence.compat import json_array_contains
from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.banner_po import SysBanner
from hei_fastapi_ddd.contexts.sys.interfaces.http.banner_schemas import (
    BannerAdminPageQuery,
    BannerCreateRequest,
    BannerPublicListQuery,
    BannerUpdateRequest,
)


class BannerRepository:
    """展示图仓储，负责直接持久化和展示查询。"""

    def __init__(self, db: AsyncSession):
        """绑定数据库会话。"""
        self.db = db

    async def create(self, payload: BannerCreateRequest) -> None:
        """新增展示图并 flush。"""
        entity = SysBanner(**payload.model_dump())
        self.db.add(entity)
        await self.db.flush()

    async def get_by_id(self, banner_id: str) -> SysBanner | None:
        """按主键查询展示图，不存在返回 None。"""
        return await self.db.get(SysBanner, banner_id)

    async def get_required(self, banner_id: str) -> SysBanner:
        """按主键查询展示图，不存在时抛出 NotFoundError。"""
        entity = await self.get_by_id(banner_id)
        if entity is None:
            raise NotFoundError("Display image not found")
        return entity

    async def update(self, payload: BannerUpdateRequest) -> None:
        """按主键更新展示图字段（排除 id）。"""
        entity = await self.get_required(payload.id)
        data = payload.model_dump(exclude={"id"})
        for key, value in data.items():
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, banner_ids: list[str]) -> None:
        """批量删除展示图（不存在的 ID 静默跳过，对齐 hei-boot 幂等语义）。"""
        unique_ids = list(dict.fromkeys(banner_ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysBanner).where(SysBanner.id.in_(unique_ids)))

    async def page_admin(self, query: BannerAdminPageQuery) -> tuple[list[SysBanner], int]:
        """按查询条件后台分页，返回记录列表与总数。"""
        stmt: Select[tuple[SysBanner]] = select(SysBanner)
        count_stmt = select(func.count(SysBanner.id))
        filters = []
        if query.target_account_type:
            filters.append(
                json_array_contains(
                    SysBanner.target_account_types,
                    str(query.target_account_type),
                )
            )
        if query.category:
            filters.append(SysBanner.category == str(query.category))
        if query.type:
            filters.append(SysBanner.type == str(query.type))
        if query.position:
            filters.append(SysBanner.position == str(query.position))
        if query.status:
            filters.append(SysBanner.status == str(query.status))
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysBanner.sort.asc(), SysBanner.id.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def list_public(
        self,
        *,
        now: datetime,
        query: BannerPublicListQuery,
        account_type: AccountType = AccountType.PORTAL,
    ) -> list[SysBanner]:
        """查询指定账户类型可见且处于展示期内的展示图列表。"""
        stmt = select(SysBanner).where(
            json_array_contains(SysBanner.target_account_types, account_type.value),
            SysBanner.status == StatusEnum.ENABLED.value,
            SysBanner.position == str(query.position),
            or_(SysBanner.start_at.is_(None), SysBanner.start_at <= now),
            or_(SysBanner.end_at.is_(None), SysBanner.end_at >= now),
        )
        if query.category:
            stmt = stmt.where(SysBanner.category == str(query.category))
        if query.type:
            stmt = stmt.where(SysBanner.type == str(query.type))
        stmt = stmt.order_by(SysBanner.sort.asc(), SysBanner.id.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def is_public_visible(
        self,
        banner_id: str,
        now: datetime,
        *,
        account_type: AccountType = AccountType.PORTAL,
    ) -> bool:
        """判断指定展示图对目标账户类型是否当前可见。"""
        stmt = select(SysBanner.id).where(
            SysBanner.id == banner_id,
            json_array_contains(SysBanner.target_account_types, account_type.value),
            SysBanner.status == StatusEnum.ENABLED.value,
            or_(SysBanner.start_at.is_(None), SysBanner.start_at <= now),
            or_(SysBanner.end_at.is_(None), SysBanner.end_at >= now),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def increment_interactions(self, deltas: dict[str, int]) -> None:
        """按 banner_id 批量累加交互次数（仅处理正增量）。"""
        positive_deltas = {banner_id: delta for banner_id, delta in deltas.items() if delta > 0}
        if not positive_deltas:
            return
        await self.db.execute(
            update(SysBanner)
            .where(SysBanner.id.in_(positive_deltas))
            .values(
                interaction_count=SysBanner.interaction_count
                + case(positive_deltas, value=SysBanner.id, else_=0)
            )
        )
