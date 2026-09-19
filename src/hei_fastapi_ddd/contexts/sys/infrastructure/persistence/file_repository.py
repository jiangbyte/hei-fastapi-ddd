"""文件仓储实现。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import Select, delete, func, inspect, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.file_po import SysFile
from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.shared.security.data_scope import build_data_scope_filter
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.storage.url import is_external_url, looks_like_presigned_url, to_object_key
from hei_fastapi_ddd.types.business import NotFoundError


def _row(entity: SysFile) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class FileRepositoryImpl:
    """文件元数据仓储实现。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        entity = SysFile(**dict(data))
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return _row(entity)

    async def get_by_object_name(self, object_name: str) -> dict[str, Any] | None:
        stmt = select(SysFile).where(SysFile.object_name == object_name)
        entity = (await self.db.execute(stmt)).scalar_one_or_none()
        return _row(entity) if entity is not None else None

    async def _get_po(self, file_id: str) -> SysFile | None:
        return await self.db.get(SysFile, file_id)

    async def get_required(self, file_id: str) -> dict[str, Any]:
        entity = await self._get_po(file_id)
        if entity is None:
            raise NotFoundError("File not found")
        return _row(entity)

    async def update(self, file_id: str, data: Mapping[str, Any]) -> None:
        entity = await self._get_po(file_id)
        if entity is None:
            raise NotFoundError("File not found")
        for key, value in data.items():
            if key == "id":
                continue
            setattr(entity, key, value)
        await self.db.flush()

    async def list_by_ids(self, file_ids: list[str]) -> list[dict[str, Any]]:
        unique_ids = list(dict.fromkeys(file_ids))
        if not unique_ids:
            return []
        stmt = select(SysFile).where(SysFile.id.in_(unique_ids))
        items = list((await self.db.execute(stmt)).scalars().all())
        return [_row(item) for item in items]

    async def list_by_object_names(self, object_names: list[str]) -> list[dict[str, Any]]:
        unique_names = list(dict.fromkeys(object_names))
        if not unique_names:
            return []
        stmt = select(SysFile).where(SysFile.object_name.in_(unique_names))
        items = list((await self.db.execute(stmt)).scalars().all())
        return [_row(item) for item in items]

    async def delete_many(self, file_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(file_ids))
        await self.db.execute(delete(SysFile).where(SysFile.id.in_(unique_ids)))

    async def delete_by_id(self, file_id: str) -> None:
        entity = await self._get_po(file_id)
        if entity is not None:
            await self.db.delete(entity)

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
        session: SessionPayload | None = None,
        permission: str = "sys:file:page",
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[SysFile]] = select(SysFile)
        count_stmt = select(func.count(SysFile.id))
        sql_filters = []
        if filters.get("original_name"):
            sql_filters.append(ci_like(SysFile.original_name, str(filters["original_name"])))
        if filters.get("object_name"):
            sql_filters.append(ci_like(SysFile.object_name, str(filters["object_name"])))
        if filters.get("storage_provider"):
            sql_filters.append(SysFile.storage_provider == filters["storage_provider"])
        if filters.get("content_type"):
            sql_filters.append(ci_like(SysFile.content_type, str(filters["content_type"])))
        if session is not None:
            scope = await build_data_scope_filter(
                self.db, session, permission, owner_column=SysFile.created_by
            )
            if scope is not None:
                sql_filters.append(scope)
        if sql_filters:
            stmt = stmt.where(*sql_filters)
            count_stmt = count_stmt.where(*sql_filters)
        stmt = stmt.order_by(SysFile.created_at.desc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return [_row(item) for item in items], total

    async def scrub_persisted_presigned_urls(self) -> int:
        rows = list((await self.db.execute(select(SysFile.id, SysFile.object_name, SysFile.url))).all())
        changed = 0
        for file_id, object_name, url in rows:
            if not url or url == object_name:
                continue
            if looks_like_presigned_url(url) or (
                is_external_url(url) and to_object_key(url) == object_name
            ):
                await self.db.execute(
                    update(SysFile).where(SysFile.id == file_id).values(url=object_name)
                )
                changed += 1
        if changed:
            await self.db.flush()
        return changed
