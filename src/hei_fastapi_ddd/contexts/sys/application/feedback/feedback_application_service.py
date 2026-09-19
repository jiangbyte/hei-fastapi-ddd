"""反馈服务层：提交、处理、查询反馈，并补充附件与提交者资料信息。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.profile.application.api.profile_read_port import ProfileReadPort
from hei_fastapi_ddd.contexts.profile.application.utils.profile import (
    get_profile,
    get_profiles_batch,
)
from hei_fastapi_ddd.contexts.sys.application.feedback.dto import (
    FeedbackAdminPageQuery,
    FeedbackCreateCommand,
    FeedbackIdQuery,
    FeedbackIdsCommand,
    FeedbackUpdateCommand,
    MyFeedbackPageQuery,
)
from hei_fastapi_ddd.contexts.sys.application.file.file_application_service import FileService
from hei_fastapi_ddd.contexts.sys.domain.feedback.repository import SysFeedbackRepository
from hei_fastapi_ddd.contexts.sys.domain.file.repository import FileRepository
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.storage.url import normalize_object_name
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import BusinessError


class SysFeedbackService:
    """反馈业务服务，编排仓储与附件/资料 enrichment。"""

    def __init__(
        self,
        db: AsyncSession,
        repo: SysFeedbackRepository,
        file_repo: FileRepository,
        file_service: FileService,
        profile_read_port: ProfileReadPort,
    ):
        self.db = db
        self.repo = repo
        self.file_repo = file_repo
        self.file_service = file_service
        self._profile_read_port = profile_read_port

    async def submit(self, command: FeedbackCreateCommand, session: SessionPayload) -> None:
        """提交反馈：推导标题/分类默认值、规范化附件名后落库。"""
        # 1. 推导标题与分类
        title = (command.title or "").strip()
        if not title:
            title = command.content.strip()[:64]
        category = (command.category or "").strip() or "GENERAL"
        # 2. 校验附件 object_name 存在
        attach_object_names = await self._normalize_attach_object_names(command.attach_object_names)
        # 3. 落库并写审计
        data: dict[str, Any] = {
            "title": title,
            "content": command.content,
            "category": category,
            "contact": command.contact,
            "attach_object_names": attach_object_names,
            "submitter_account_type": str(session.account_type),
            "submitter_account_id": session.account_id,
        }
        async with transactional(self.db):
            row = await self.repo.create(data)
            audit_snapshots.created_entity(row)

    async def update(self, command: FeedbackUpdateCommand, session: SessionPayload) -> None:
        """处理反馈：更新状态或回复内容。"""
        before = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(before)
        patch: dict[str, Any] = {}
        if command.status is not None:
            patch["status"] = command.status
        if command.reply is not None:
            patch["reply"] = command.reply
            patch["replied_by"] = session.account_id
            patch["replied_at"] = datetime.now(UTC)
        async with transactional(self.db):
            if patch:
                await self.repo.update(command.id, patch)
            after = await self.repo.get_required(command.id)
            audit_snapshots.after_entity(after)

    async def delete(self, command: FeedbackIdsCommand) -> None:
        """批量删除反馈。"""
        unique_ids = list(dict.fromkeys(command.ids))
        entities = [
            row
            for entity_id in unique_ids
            if (row := await self.repo.get_by_id(entity_id)) is not None
        ]
        async with transactional(self.db):
            audit_snapshots.deleted_all(entities)
            await self.repo.delete_many(unique_ids)

    async def detail(self, query: FeedbackIdQuery) -> dict[str, Any]:
        """管理端查询反馈详情，并补充附件与提交者资料。"""
        row = await self.repo.get_required(query.id)
        return await self._enrich_profiles(dict(row))

    async def detail_my(self, query: FeedbackIdQuery, session: SessionPayload) -> dict[str, Any]:
        """查询「我的反馈」详情，非本人反馈返回无权查看。"""
        row = await self.repo.get_required(query.id)
        if (
            str(row.get("submitter_account_type")) != str(session.account_type)
            or str(row.get("submitter_account_id")) != str(session.account_id)
        ):
            raise BusinessError("无权查看")
        enriched = await self._enrich_attachments(dict(row))
        return enriched

    async def page_admin(self, query: FeedbackAdminPageQuery) -> PageData[dict[str, Any]]:
        """管理端分页查询反馈，并批量补充提交者资料。"""
        filters = query.model_dump(exclude={"page", "size", "offset"})
        items, total = await self.repo.page_admin(
            filters, offset=query.offset, limit=query.size
        )
        records = await self._batch_enrich_profiles([dict(i) for i in items])
        return build_page(query, total, records)

    async def page_my(
        self,
        query: MyFeedbackPageQuery,
        session: SessionPayload,
    ) -> PageData[dict[str, Any]]:
        """分页查询「我的反馈」，并补充附件信息。"""
        filters = query.model_dump(exclude={"page", "size", "offset"})
        items, total = await self.repo.page_my(
            filters,
            account_type=str(session.account_type),
            account_id=session.account_id,
            offset=query.offset,
            limit=query.size,
        )
        records = await self._batch_enrich_profiles([dict(i) for i in items])
        return build_page(query, total, records)

    async def _normalize_attach_object_names(self, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            object_name = normalize_object_name(value)
            if object_name:
                normalized.append(object_name)
        unique = list(dict.fromkeys(normalized))
        if not unique:
            return []
        rows = await self.file_repo.list_by_object_names(unique)
        found = {row["object_name"] for row in rows}
        missing = [name for name in unique if name not in found]
        if missing:
            raise BusinessError("附件文件不存在")
        return unique

    async def _enrich_attachments(self, row: dict[str, Any]) -> dict[str, Any]:
        rows = await self._enrich_attachments_many([row])
        return rows[0]

    async def _enrich_attachments_many(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        all_names: list[str] = []
        for row in rows:
            names = [
                name
                for raw in (row.get("attach_object_names") or [])
                if (name := normalize_object_name(str(raw)))
            ]
            row["attach_object_names"] = list(dict.fromkeys(names))
            all_names.extend(row["attach_object_names"])

        entity_map = {
            r["object_name"]: r
            for r in await self.file_repo.list_by_object_names(all_names)
        }
        url_map = await self.file_service.resolve_access_urls(all_names)
        for row in rows:
            attachments: list[dict[str, Any]] = []
            for object_name in row.get("attach_object_names") or []:
                entity = entity_map.get(object_name)
                resolved = url_map.get(object_name)
                if entity is None:
                    attachments.append({"object_name": object_name, "url": resolved})
                    continue
                attachments.append(
                    {
                        "object_name": entity["object_name"],
                        "id": entity.get("id"),
                        "original_name": entity.get("original_name"),
                        "content_type": entity.get("content_type"),
                        "size": entity.get("size"),
                        "url": resolved,
                    }
                )
            row["attachments"] = attachments
        return rows

    async def _enrich_profiles(self, row: dict[str, Any]) -> dict[str, Any]:
        await self._enrich_attachments(row)
        submitter_id = row.get("submitter_account_id")
        if submitter_id:
            try:
                at = AccountType(str(row.get("submitter_account_type")))
                profile = await get_profile(self._profile_read_port, at, str(submitter_id))
                if profile:
                    avatar = profile.get("avatar")
                    row["submitter_avatar"] = await self.file_service.resolve_access_url(
                        str(avatar) if avatar else None
                    )
                    row["submitter_nickname"] = profile.get("nickname") or profile.get("name")
            except ValueError:
                pass
        return row

    async def _batch_enrich_profiles(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        await self._enrich_attachments_many(rows)
        groups: dict[str, list[str]] = {}
        schema_map: list[tuple[dict[str, Any], str]] = []
        for row in rows:
            sid = row.get("submitter_account_id")
            stype = row.get("submitter_account_type")
            if sid and stype:
                groups.setdefault(str(stype), []).append(str(sid))
                schema_map.append((row, str(stype)))
        for account_type_str, account_ids in groups.items():
            try:
                at = AccountType(account_type_str)
                batch = await get_profiles_batch(self._profile_read_port, at, account_ids)
                avatars = [
                    str(batch[aid]["avatar"])
                    for aid in account_ids
                    if aid in batch and batch[aid].get("avatar")
                ]
                url_map = await self.file_service.resolve_access_urls(avatars)
                for row, _ in schema_map:
                    if (
                        str(row.get("submitter_account_type")) == account_type_str
                        and str(row.get("submitter_account_id")) in batch
                    ):
                        p = batch[str(row.get("submitter_account_id"))]
                        raw = str(p.get("avatar") or "").strip()
                        row["submitter_avatar"] = url_map.get(raw) if raw else None
                        row["submitter_nickname"] = p.get("nickname") or p.get("name")
            except ValueError:
                pass
        return rows
