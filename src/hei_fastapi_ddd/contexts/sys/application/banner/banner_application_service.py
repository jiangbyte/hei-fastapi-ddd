"""展示图应用服务。"""

from __future__ import annotations

from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.banner.dto import (
    BannerAdminPageQuery,
    BannerCreateCommand,
    BannerPublicListQuery,
    BannerUpdateCommand,
)
from hei_fastapi_ddd.contexts.sys.application.file.file_application_service import FileService
from hei_fastapi_ddd.contexts.sys.domain.banner.repository import BannerRepository
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.redis.keys import banner_interaction_delta_key
from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.shared.storage.url import normalize_object_name
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import BusinessError, NotFoundError


class BannerService:
    def __init__(self, db: AsyncSession, repo: BannerRepository, file_service: FileService):
        self.db = db
        self.repo = repo
        self.file_service = file_service

    async def create(self, command: BannerCreateCommand) -> None:
        data = command.model_dump()
        data["image"] = normalize_object_name(command.image) or command.image
        async with transactional(self.db):
            row = await self.repo.create(data)
            audit_snapshots.created_entity(row)

    async def update(self, command: BannerUpdateCommand) -> None:
        before = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(before)
        data = command.model_dump(exclude={"id"})
        data["image"] = normalize_object_name(command.image) or command.image
        async with transactional(self.db):
            await self.repo.update(command.id, data)
            audit_snapshots.after_entity(await self.repo.get_required(command.id))

    async def delete(self, ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(ids))
        rows = [r for i in unique_ids if (r := await self.repo.get_by_id(i))]
        async with transactional(self.db):
            audit_snapshots.deleted_all(rows)
            await self.repo.delete_many(unique_ids)

    async def detail(self, banner_id: str) -> dict:
        row = await self.repo.get_required(banner_id)
        return await self._resolve_image_urls([row])[0]

    async def page_admin(self, query: BannerAdminPageQuery) -> PageData[dict]:
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
        )
        records = await self._resolve_image_urls(items)
        return build_page(query, total, records)  # type: ignore[arg-type]

    async def list_visible(
        self, query: BannerPublicListQuery, *, account_type: AccountType
    ) -> list[dict]:
        items = await self.repo.list_public(
            now=datetime.now(UTC),
            filters=query.model_dump(),
            account_type=account_type.value,
        )
        return await self._resolve_image_urls(items)

    async def record_interaction(self, banner_id: str, *, account_type: AccountType) -> None:
        if await self.repo.get_by_id(banner_id) is None:
            raise NotFoundError("Display image not found")
        if not await self.repo.is_public_visible(
            banner_id, datetime.now(UTC), account_type=account_type.value
        ):
            raise BusinessError("Banner is not publicly visible")
        redis = get_redis()
        if redis is None:
            return
        await redis.hincrby(banner_interaction_delta_key(), banner_id, 1)

    async def flush_interaction_deltas(self, redis: Redis) -> int:
        key = banner_interaction_delta_key()
        raw_values = await redis.hgetall(key)
        if not raw_values:
            return 0
        deltas: dict[str, int] = {}
        for raw_id, raw_delta in raw_values.items():
            banner_id = raw_id.decode() if isinstance(raw_id, bytes) else str(raw_id)
            delta_text = raw_delta.decode() if isinstance(raw_delta, bytes) else str(raw_delta)
            try:
                delta = int(delta_text)
            except ValueError:
                continue
            if delta > 0:
                deltas[banner_id] = delta
        if not deltas:
            return 0
        async with transactional(self.db):
            await self.repo.increment_interactions(deltas)
        await redis.hdel(key, *deltas.keys())
        return len(deltas)

    async def _resolve_image_urls(self, items: list[dict]) -> list[dict]:
        urls = await self.file_service.resolve_access_urls([i.get("image") for i in items])
        for item in items:
            raw = str(item.get("image") or "").strip()
            item["image_url"] = urls.get(raw) if raw else None
        return items

