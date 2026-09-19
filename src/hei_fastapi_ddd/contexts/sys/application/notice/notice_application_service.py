""" Author: Charlie

消息通知应用服务：创建、发布、撤回、置顶与阅读状态管理。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.notice.dto import (
    MyNoticePageQuery,
    NoticeAdminPageQuery,
    NoticeCreateCommand,
    NoticeReadCommand,
    NoticeUpdateCommand,
    PinNoticeCommand,
)
from hei_fastapi_ddd.contexts.sys.domain.notice.enums import NoticeKind, NoticeStatus
from hei_fastapi_ddd.contexts.sys.domain.notice.repository import NoticeRepository
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import BusinessError, NotFoundError


class SysNoticeService:
    """消息通知业务服务。"""

    def __init__(self, db: AsyncSession, repo: NoticeRepository):
        self.db = db
        self.repo = repo

    async def create(self, command: NoticeCreateCommand) -> None:
        """创建消息：规范化状态，并在发布时补写发布时间。"""
        # 1. 归一化状态与发布时间
        data = command.model_dump()
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
        # 2. 事务内持久化并写审计
        async with transactional(self.db):
            row = await self.repo.create(data)
            audit_snapshots.created_entity(row)

    async def update(self, command: NoticeUpdateCommand) -> None:
        """更新消息：归一状态并在发布时回填发布时间。"""
        # 1. 审计前快照
        before = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(before)
        data = command.model_dump(
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
        # 2. 事务内更新并写后快照
        async with transactional(self.db):
            await self.repo.update(command.id, data)
            after = await self.repo.get_required(command.id)
            audit_snapshots.after_entity(after)

    async def delete(self, ids: list[str]) -> None:
        """批量删除消息。"""
        unique_ids = list(dict.fromkeys(ids))
        entities = [
            row
            for entity_id in unique_ids
            if (row := await self.repo.get_by_id(entity_id)) is not None
        ]
        async with transactional(self.db):
            audit_snapshots.deleted_all(entities)
            await self.repo.delete_many(unique_ids)

    async def detail(self, notice_id: str) -> dict:
        """管理端查询消息详情。"""
        return await self.repo.get_required(notice_id)

    async def page_admin(self, query: NoticeAdminPageQuery) -> PageData[dict]:
        """管理端分页查询消息。"""
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
        )
        return build_page(query, total, items)  # type: ignore[arg-type]

    async def publish(self, ids: list[str], session: SessionPayload) -> None:
        """发布消息，记录发布时间与发送者。"""
        unique_ids = list(dict.fromkeys(ids))
        if unique_ids:
            audit_snapshots.before_entity(await self.repo.get_required(unique_ids[0]))
        async with transactional(self.db):
            await self.repo.publish_many(
                ids,
                now=datetime.now(UTC),
                sender_account_type=str(session.account_type),
                sender_account_id=session.account_id,
            )
        if unique_ids:
            audit_snapshots.after_entity(await self.repo.get_required(unique_ids[0]))

    async def revoke(self, ids: list[str]) -> None:
        """撤回消息，记录撤回时间。"""
        unique_ids = list(dict.fromkeys(ids))
        if unique_ids:
            audit_snapshots.before_entity(await self.repo.get_required(unique_ids[0]))
        async with transactional(self.db):
            await self.repo.revoke_many(ids, now=datetime.now(UTC))
        if unique_ids:
            audit_snapshots.after_entity(await self.repo.get_required(unique_ids[0]))

    async def pin(self, command: PinNoticeCommand) -> None:
        """置顶/取消置顶公告（仅公告支持置顶）。"""
        # 1. 校验类型并写审计
        row = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(row)
        if row.get("kind") != NoticeKind.ANNOUNCEMENT.value:
            raise BusinessError("仅公告支持置顶")
        async with transactional(self.db):
            after = await self.repo.update_pin(
                command.id,
                is_pinned=command.is_pinned,
                pinned_until=command.pinned_until,
            )
            audit_snapshots.after_entity(after)

    async def page_my(
        self,
        query: MyNoticePageQuery,
        session: SessionPayload,
    ) -> PageData[dict]:
        """分页查询当前用户可见消息，并标记是否已读。"""
        items, total, read_id_set = await self.repo.page_my(
            query.model_dump(exclude={"current", "size"}),
            str(session.account_type),
            session.account_id,
            offset=query.offset,
            limit=query.size,
        )
        records = [_with_read_flag(item, read_id_set) for item in items]
        return build_page(query, total, records)  # type: ignore[arg-type]

    async def page_portal_list(
        self,
        query: MyNoticePageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[dict]:
        """门户列表页查询公告。"""
        if session is not None:
            account_type = str(session.account_type)
            account_id = session.account_id
        else:
            account_type = AccountType.PORTAL.value
            account_id = None
        items, total, read_id_set = await self.repo.page_my(
            query.model_dump(exclude={"current", "size"}),
            account_type,
            account_id,
            kind=NoticeKind.ANNOUNCEMENT.value,
            offset=query.offset,
            limit=query.size,
        )
        records = [_with_read_flag(item, read_id_set) for item in items]
        return build_page(query, total, records)  # type: ignore[arg-type]

    async def my_detail(self, notice_id: str, session: SessionPayload) -> dict:
        """查询当前用户消息详情并标记已读。"""
        async with transactional(self.db):
            visible = await self.repo.find_published_visible(
                notice_id, str(session.account_type), session.account_id
            )
            if visible is None:
                raise NotFoundError("SysNotice not found")
            await self.repo.increment_view_count(notice_id)
            await self.repo.mark_read([notice_id], str(session.account_type), session.account_id)
        read_set = await self.repo.list_read_ids(
            [str(visible["id"])], str(session.account_type), session.account_id
        )
        return _with_read_flag(visible, read_set)

    async def count_unread(self, session: SessionPayload) -> int:
        """统计当前用户未读消息数。"""
        return await self.repo.count_unread(str(session.account_type), session.account_id)

    async def mark_read(self, command: NoticeReadCommand, session: SessionPayload) -> None:
        """将指定消息标记为当前用户已读。"""
        async with transactional(self.db):
            await self.repo.mark_read(command.ids, str(session.account_type), session.account_id)

    async def mark_all_read(self, session: SessionPayload) -> None:
        """将当前用户全部可见消息标记为已读。"""
        async with transactional(self.db):
            await self.repo.mark_all_read(str(session.account_type), session.account_id)


def _with_read_flag(item: dict, read_id_set: set[str]) -> dict:
    """为消息行附加 is_read 标记。"""
    row = dict(item)
    row["is_read"] = str(row.get("id")) in read_id_set
    return row
