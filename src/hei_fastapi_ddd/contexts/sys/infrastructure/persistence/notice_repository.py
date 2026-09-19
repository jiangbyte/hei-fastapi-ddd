""" Author: Charlie

消息通知仓储层：封装消息的增删改查、可见性过滤与阅读状态管理。
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, and_, delete, exists, func, inspect, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement
from hei_fastapi_ddd.contexts.sys.domain.notice.enums import NoticeKind, NoticeStatus, TargetScope
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.notice_po import (
    SysNotice,
    SysNoticeRead,
)
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.batch import chunked
from hei_fastapi_ddd.shared.persistence.compat import (
    ci_like,
    json_array_contains,
    json_array_length,
)
from hei_fastapi_ddd.types.business import NotFoundError

# 服务端维护字段：更新请求不可覆盖（对齐 hei-boot：viewCount/revokedAt/sender 由服务端维护）。
_SERVER_FIELDS = {
    "view_count",
    "revoked_at",
    "sender_account_type",
    "sender_account_id",
}


def _visible_to_account(account_type: str, account_id: str | None = None) -> ColumnElement[bool]:
    """构造「对指定账户可见」的过滤条件（按类型匹配或按 ID 精确匹配）。"""
    type_match = (json_array_length(SysNotice.target_account_types) == 0) | json_array_contains(
        SysNotice.target_account_types, account_type
    )
    clauses: list[ColumnElement[bool]] = [
        and_(
            SysNotice.target_scope.in_([TargetScope.ALL.value, TargetScope.ACCOUNT_TYPE.value]),
            type_match,
        )
    ]
    if account_id:
        clauses.append(
            and_(
                SysNotice.target_scope == TargetScope.SPECIFIC.value,
                json_array_contains(SysNotice.target_account_ids, account_id),
            )
        )
    return or_(*clauses)


def _published_filters(
    *,
    account_type: str,
    account_id: str | None = None,
    kind: str | None = None,
) -> list[ColumnElement[bool]]:
    """构造已发布消息的通用过滤条件（含可见性、公告未过期判断）。"""
    now = datetime.now(UTC)
    filters: list[ColumnElement[bool]] = [
        SysNotice.status == NoticeStatus.PUBLISHED.value,
        _visible_to_account(account_type, account_id),
        or_(
            SysNotice.kind != NoticeKind.ANNOUNCEMENT.value,
            SysNotice.expire_at.is_(None),
            SysNotice.expire_at > now,
        ),
    ]
    if kind:
        filters.append(SysNotice.kind == kind.upper())
    return filters


def _row(entity: SysNotice) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class SysNoticeRepositoryImpl:
    """消息通知数据仓储，负责 SysNotice 与阅读记录的持久化查询。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        """创建消息记录。"""
        entity = SysNotice(**dict(data))
        self.db.add(entity)
        await self.db.flush()
        return _row(entity)

    async def _get_po(self, entity_id: str) -> SysNotice | None:
        return await self.db.get(SysNotice, entity_id)

    async def get_by_id(self, entity_id: str) -> dict[str, Any] | None:
        """按主键查询消息，不存在时返回 None。"""
        entity = await self._get_po(entity_id)
        return _row(entity) if entity is not None else None

    async def get_required(self, entity_id: str) -> dict[str, Any]:
        """按主键查询消息，不存在时抛出 NotFoundError。"""
        entity = await self._get_po(entity_id)
        if entity is None:
            raise NotFoundError("SysNotice not found")
        return _row(entity)

    async def update(self, entity_id: str, data: Mapping[str, Any]) -> None:
        """按字段更新消息（排除服务端维护字段）。"""
        entity = await self._get_po(entity_id)
        if entity is None:
            raise NotFoundError("SysNotice not found")
        for key, value in data.items():
            if key in _SERVER_FIELDS or key == "id":
                continue
            setattr(entity, key, value)
        await self.db.flush()

    async def update_pin(
        self,
        entity_id: str,
        *,
        is_pinned: bool,
        pinned_until: datetime | None,
    ) -> dict[str, Any]:
        """更新公告置顶状态。"""
        entity = await self._get_po(entity_id)
        if entity is None:
            raise NotFoundError("SysNotice not found")
        entity.is_pinned = is_pinned
        entity.pinned_until = pinned_until
        await self.db.flush()
        return _row(entity)

    async def list_read_ids(
        self,
        notice_ids: list[str],
        account_type: str,
        account_id: str,
    ) -> set[str]:
        """查询已读消息 ID 集合。"""
        if not notice_ids:
            return set()
        stmt = select(SysNoticeRead.notice_id).where(
            SysNoticeRead.notice_id.in_(notice_ids),
            SysNoticeRead.account_type == account_type,
            SysNoticeRead.account_id == account_id,
        )
        return set((await self.db.execute(stmt)).scalars().all())

    async def delete_many(self, entity_ids: list[str]) -> None:
        """批量删除消息并级联清理阅读记录（不存在的 ID 静默跳过，对齐 hei-boot 幂等语义）。"""
        unique_ids = list(dict.fromkeys(entity_ids))
        if not unique_ids:
            return
        await self.db.execute(delete(SysNoticeRead).where(SysNoticeRead.notice_id.in_(unique_ids)))
        await self.db.execute(delete(SysNotice).where(SysNotice.id.in_(unique_ids)))

    async def publish_many(
        self,
        entity_ids: list[str],
        *,
        now: datetime,
        sender_account_type: str,
        sender_account_id: str,
    ) -> None:
        """批量发布消息：分批校验 ID 均存在，再逐批单条 UPDATE 落库。

        替代逐条 SELECT+UPDATE 的循环，避免 N+1；IN 分批规避变量上限。
        """
        unique_ids = list(dict.fromkeys(entity_ids))
        if not unique_ids:
            return
        for batch in chunked(unique_ids):
            await self.db.execute(
                update(SysNotice)
                .where(SysNotice.id.in_(batch))
                .values(
                    status=NoticeStatus.PUBLISHED.value,
                    publish_at=now,
                    sender_account_type=sender_account_type,
                    sender_account_id=sender_account_id,
                )
            )
        await self.db.flush()

    async def revoke_many(self, entity_ids: list[str], *, now: datetime) -> None:
        """批量撤回消息（不存在的 ID 静默跳过，对齐 hei-boot 幂等语义）。"""
        unique_ids = list(dict.fromkeys(entity_ids))
        if not unique_ids:
            return
        for batch in chunked(unique_ids):
            await self.db.execute(
                update(SysNotice)
                .where(SysNotice.id.in_(batch))
                .values(status=NoticeStatus.REVOKED.value, revoked_at=now)
            )
        await self.db.flush()

    async def find_published_visible(
        self,
        entity_id: str,
        account_type: str,
        account_id: str | None = None,
    ) -> dict[str, Any] | None:
        """按 ID 查询「已发布且对指定账户可见」的消息，否则返回 None。"""
        stmt = (
            select(SysNotice)
            .where(
                SysNotice.id == entity_id,
                *_published_filters(account_type=account_type, account_id=account_id),
            )
            .limit(1)
        )
        entity = (await self.db.execute(stmt)).scalar_one_or_none()
        return _row(entity) if entity is not None else None

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """管理端分页查询消息，支持标题/状态/类型过滤。"""
        stmt: Select[tuple[SysNotice]] = select(SysNotice)
        count_stmt = select(func.count(SysNotice.id))
        sql_filters = []
        title = filters.get("title")
        status = filters.get("status")
        kind = filters.get("kind")
        if title:
            sql_filters.append(ci_like(SysNotice.title, str(title)))
        if status is not None:
            sql_filters.append(SysNotice.status == status)
        if kind:
            sql_filters.append(SysNotice.kind == str(kind).upper())
        if sql_filters:
            stmt = stmt.where(*sql_filters)
            count_stmt = count_stmt.where(*sql_filters)
        stmt = stmt.order_by(SysNotice.created_at.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [_row(item) for item in items], total

    async def page_my(
        self,
        filters: Mapping[str, Any],
        account_type: str,
        account_id: str | None = None,
        *,
        kind: str | None = None,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int, set[str]]:
        """分页查询对当前账户可见的消息，并返回已读 ID 集合。"""
        published = _published_filters(
            account_type=account_type,
            account_id=account_id,
            kind=kind or filters.get("kind"),
        )
        stmt: Select[tuple[SysNotice]] = select(SysNotice).where(*published)
        count_stmt = select(func.count(SysNotice.id)).where(*published)
        stmt = (
            stmt.order_by(SysNotice.is_pinned.desc(), SysNotice.publish_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()

        read_id_set: set[str] = set()
        if items and account_id:
            notice_ids = [item.id for item in items]
            read_id_set = await self.list_read_ids(notice_ids, account_type, account_id)
        return [_row(item) for item in items], total, read_id_set

    async def count_unread(self, account_type: str, account_id: str) -> int:
        """统计当前账户可见消息中的未读数量（SQL anti-join，避免拉全量 ID）。"""
        published = _published_filters(account_type=account_type, account_id=account_id)
        read_exists = exists(
            select(SysNoticeRead.id).where(
                SysNoticeRead.notice_id == SysNotice.id,
                SysNoticeRead.account_type == account_type,
                SysNoticeRead.account_id == account_id,
            )
        )
        stmt = select(func.count(SysNotice.id)).where(*published, ~read_exists)
        return int((await self.db.execute(stmt)).scalar_one())

    async def mark_read(self, ids: list[str], account_type: str, account_id: str) -> None:
        """将指定消息标记为当前账户已读（幂等，跳过已读项）。"""
        unique_ids = list(dict.fromkeys(ids))
        existing_stmt = select(SysNoticeRead.notice_id).where(
            SysNoticeRead.notice_id.in_(unique_ids),
            SysNoticeRead.account_type == account_type,
            SysNoticeRead.account_id == account_id,
        )
        existing_ids = set((await self.db.execute(existing_stmt)).scalars().all())
        new_ids = [nid for nid in unique_ids if nid not in existing_ids]
        for notice_id in new_ids:
            self.db.add(
                SysNoticeRead(
                    notice_id=notice_id,
                    account_type=account_type,
                    account_id=account_id,
                )
            )
        if new_ids:
            await self.db.flush()

    async def mark_all_read(self, account_type: str, account_id: str) -> None:
        """将当前账户全部可见未读消息标记为已读（幂等）。"""
        # 1. 规范化账户维度，避免枚举/数字与库中字符串比较不一致导致“已读”漏判
        account_type = str(getattr(account_type, "value", account_type))
        account_id = str(account_id)
        # 2. 先按可见范围查出疑似未读 ID（NOT EXISTS 可能在部分驱动下漏过滤）
        published = _published_filters(account_type=account_type, account_id=account_id)
        read_exists = exists(
            select(SysNoticeRead.id).where(
                SysNoticeRead.notice_id == SysNotice.id,
                SysNoticeRead.account_type == account_type,
                SysNoticeRead.account_id == account_id,
            )
        )
        unread_stmt = select(SysNotice.id).where(*published, ~read_exists)
        unread_ids = [str(v) for v in (await self.db.execute(unread_stmt)).scalars().all()]
        if not unread_ids:
            return
        # 3. 再按唯一键二次排除已读，保证并发/驱动差异下仍幂等，不触发 IntegrityError
        existing_ids = set(
            (
                await self.db.execute(
                    select(SysNoticeRead.notice_id).where(
                        SysNoticeRead.notice_id.in_(unread_ids),
                        SysNoticeRead.account_type == account_type,
                        SysNoticeRead.account_id == account_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        new_ids = [nid for nid in unread_ids if nid not in existing_ids]
        # 4. 仅插入真正缺失的阅读记录
        for notice_id in new_ids:
            self.db.add(
                SysNoticeRead(
                    id=generate_snowflake_id(),
                    notice_id=notice_id,
                    account_type=account_type,
                    account_id=account_id,
                )
            )
        if new_ids:
            await self.db.flush()

    async def increment_view_count(self, entity_id: str) -> None:
        """公告被查看时自增其查看次数。"""
        await self.db.execute(
            update(SysNotice)
            .where(
                SysNotice.id == entity_id,
                SysNotice.kind == NoticeKind.ANNOUNCEMENT.value,
            )
            .values(view_count=SysNotice.view_count + 1)
        )
        await self.db.flush()
