""" Author: Charlie

消息通知服务层：创建、发布、撤回、置顶与阅读状态管理。
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.domain.notice.enums import NoticeKind, NoticeStatus
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.notice_po import SysNoticeRead
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.notice_repository import (
    SysNoticeRepository,
)
from hei_fastapi_ddd.contexts.sys.interfaces.http.notice_schemas import (
    MyNoticePageQuery,
    NoticeReadRequest,
    PinNoticeRequest,
    SysNoticeAdminPageQuery,
    SysNoticeCreateRequest,
    SysNoticeSchema,
    SysNoticeUpdateRequest,
)
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.exceptions.business import BusinessError, NotFoundError
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, to_schema, to_schema_list
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page


class SysNoticeService:
    """消息通知业务服务，编排仓储并提供发布/阅读等用例。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SysNoticeRepository(db)

    async def create(self, payload: SysNoticeCreateRequest) -> None:
        """创建消息：规范化状态，并在发布时补写发布时间。"""
        async with transactional(self.db):
            data = payload.model_dump()
            status = str(data.get("status") or NoticeStatus.DRAFT.value).upper()
            if status in {"ENABLED", "ENABLE"}:
                status = NoticeStatus.DRAFT.value
            if status not in {
                NoticeStatus.DRAFT.value,
                NoticeStatus.PUBLISHED.value,
                NoticeStatus.REVOKED.value,
            }:
                status = NoticeStatus.DRAFT.value
            data["status"] = status
            if status == NoticeStatus.PUBLISHED.value and not data.get("publish_at"):
                data["publish_at"] = datetime.now(UTC)
            entity = await self.repo.create(SysNoticeCreateRequest(**data))
            audit_snapshots.created_entity(entity)

    async def update(self, payload: SysNoticeUpdateRequest) -> None:
        """更新消息：归一状态并在发布时回填发布时间（对齐 hei-boot）。"""
        entity = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(entity)
        async with transactional(self.db):
            data = payload.model_dump(
                exclude={
                    "id",
                    "view_count",
                    "revoked_at",
                    "sender_account_type",
                    "sender_account_id",
                }
            )
            status = str(data.get("status") or NoticeStatus.DRAFT.value).upper()
            if status in {"ENABLED", "ENABLE"}:
                status = NoticeStatus.DRAFT.value
            if status not in {
                NoticeStatus.DRAFT.value,
                NoticeStatus.PUBLISHED.value,
                NoticeStatus.REVOKED.value,
            }:
                status = NoticeStatus.DRAFT.value
            data["status"] = status
            if status == NoticeStatus.PUBLISHED.value and not data.get("publish_at"):
                data["publish_at"] = datetime.now(UTC)
            await self.repo.update(SysNoticeUpdateRequest(id=payload.id, **data))
            await self.db.refresh(entity)
            audit_snapshots.after_entity(entity)

    async def delete(self, payload: IdsRequest) -> None:
        """批量删除消息。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = [
            entity
            for entity_id in unique_ids
            if (entity := await self.repo.get_by_id(entity_id)) is not None
        ]
        async with transactional(self.db):
            audit_snapshots.deleted_all(entities)
            await self.repo.delete_many(unique_ids)

    async def detail(self, query: IdQuery) -> SysNoticeSchema:
        """管理端查询消息详情，并补充审计人姓名。"""
        entity = await self.repo.get_required(query.id)
        schema = to_schema(SysNoticeSchema, entity)
        return schema

    async def page_admin(self, query: SysNoticeAdminPageQuery) -> PageData[SysNoticeSchema]:
        """管理端分页查询消息。"""
        items, total = await self.repo.page_admin(query)
        schemas = to_schema_list(SysNoticeSchema, items)
        return build_page(query, total, schemas)

    async def publish(self, payload: IdsRequest, session: SessionPayload) -> None:
        """发布消息，记录发布时间与发送者（批量单条 UPDATE）。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = [await self.repo.get_required(entity_id) for entity_id in unique_ids]
        if entities:
            audit_snapshots.before_entity(entities[0])
        async with transactional(self.db):
            await self.repo.publish_many(
                payload.ids,
                now=datetime.now(UTC),
                sender_account_type=str(session.account_type),
                sender_account_id=session.account_id,
            )
        for entity in entities:
            await self.db.refresh(entity)
        if entities:
            audit_snapshots.after_entity(entities[0])

    async def revoke(self, payload: IdsRequest) -> None:
        """撤回消息，记录撤回时间（批量单条 UPDATE）。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = [await self.repo.get_required(entity_id) for entity_id in unique_ids]
        if entities:
            audit_snapshots.before_entity(entities[0])
        async with transactional(self.db):
            await self.repo.revoke_many(payload.ids, now=datetime.now(UTC))
        for entity in entities:
            await self.db.refresh(entity)
        if entities:
            audit_snapshots.after_entity(entities[0])

    async def pin(self, payload: PinNoticeRequest) -> None:
        """置顶/取消置顶公告（仅公告支持置顶）。"""
        entity = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(entity)
        async with transactional(self.db):
            if entity.kind != NoticeKind.ANNOUNCEMENT.value:
                raise BusinessError("仅公告支持置顶")
            entity.is_pinned = payload.is_pinned
            entity.pinned_until = payload.pinned_until
            await self.db.flush()
            audit_snapshots.after_entity(entity)

    async def page_my(
        self,
        query: MyNoticePageQuery,
        session: SessionPayload,
    ) -> PageData[SysNoticeSchema]:
        """分页查询当前用户可见消息，并标记是否已读。"""
        items, total, read_id_set = await self.repo.page_my(
            query,
            str(session.account_type),
            session.account_id,
        )
        schemas = [_build_schema(item, read_id_set) for item in items]
        return build_page(query, total, schemas)

    async def page_portal_list(
        self,
        query: MyNoticePageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[SysNoticeSchema]:
        """门户列表页查询公告（匿名可见，登录后按会话身份过滤，对齐 hei-boot）。"""
        if session is not None:
            account_type = str(session.account_type)
            account_id = session.account_id
        else:
            account_type = AccountType.PORTAL.value
            account_id = None
        items, total, read_id_set = await self.repo.page_my(
            query,
            account_type,
            account_id,
            kind=NoticeKind.ANNOUNCEMENT.value,
        )
        schemas = [_build_schema(item, read_id_set) for item in items]
        return build_page(query, total, schemas)

    async def my_detail(self, query: IdQuery, session: SessionPayload) -> SysNoticeSchema:
        """查询当前用户消息详情。

        仅已发布且对当前账户可见的消息可读（否则 404），通过后再自增查看数并标记已读，
        对齐 hei-boot 的 myDetail 语义。
        """
        async with transactional(self.db):
            visible = await self.repo.find_published_visible(
                query.id, str(session.account_type), session.account_id
            )
            if visible is None:
                raise NotFoundError("SysNotice not found")
            await self.repo.increment_view_count(query.id)
            await self.repo.mark_read([query.id], str(session.account_type), session.account_id)
        read_set = await self._check_read([visible.id], session)
        return _build_schema(visible, read_set)

    async def count_unread(self, session: SessionPayload) -> int:
        """统计当前用户未读消息数。"""
        return await self.repo.count_unread(str(session.account_type), session.account_id)

    async def mark_read(self, payload: NoticeReadRequest, session: SessionPayload) -> None:
        """将指定消息标记为当前用户已读。"""
        async with transactional(self.db):
            await self.repo.mark_read(payload.ids, str(session.account_type), session.account_id)

    async def mark_all_read(self, session: SessionPayload) -> None:
        """将当前用户全部可见消息标记为已读。"""
        async with transactional(self.db):
            await self.repo.mark_all_read(str(session.account_type), session.account_id)

    async def _check_read(self, notice_ids: list[str], session: SessionPayload) -> set[str]:
        """查询给定消息中已被当前用户阅读的 ID 集合。"""
        if not notice_ids:
            return set()
        stmt = select(SysNoticeRead.notice_id).where(
            SysNoticeRead.notice_id.in_(notice_ids),
            SysNoticeRead.account_type == str(session.account_type),
            SysNoticeRead.account_id == session.account_id,
        )
        return set((await self.db.execute(stmt)).scalars().all())


def _build_schema(item, read_id_set: set[str]) -> SysNoticeSchema:
    """由实体构建消息响应，并标记是否已读。"""
    schema = to_schema(SysNoticeSchema, item)
    schema.is_read = item.id in read_id_set
    return schema
