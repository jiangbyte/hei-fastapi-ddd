""" Author: Charlie

文件仓储层：封装文件元数据的持久化、查询与分页。
"""

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.file_po import SysFile
from hei_fastapi_ddd.contexts.sys.interfaces.http.file_schemas import (
    FileAdminPageQuery,
    FileRecordCreate,
    FileUpdateRequest,
)
from hei_fastapi_ddd.shared.exceptions.business import NotFoundError
from hei_fastapi_ddd.shared.persistence.compat import ci_like


class FileRepository:
    """文件仓储，负责对象存储元数据的持久化和查询。"""

    def __init__(self, db: AsyncSession):
        """绑定数据库会话。"""
        self.db = db

    async def create(self, payload: FileRecordCreate) -> SysFile:
        """创建文件元数据记录，避免仓储继续接收长平铺参数列表。"""
        entity = SysFile(**payload.model_dump())
        self.db.add(entity)
        await self.db.flush()
        # 显式 refresh：避免仅 server_default 时异步惰性加载 MissingGreenlet
        await self.db.refresh(entity)
        return entity

    async def get_by_object_name(self, object_name: str) -> SysFile | None:
        """按对象名查询文件元数据，用于 URL 查询和删除逻辑。"""
        stmt = select(SysFile).where(SysFile.object_name == object_name)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, file_id: str) -> SysFile | None:
        """按文件 ID 获取文件元数据。"""
        return await self.db.get(SysFile, file_id)

    async def get_required(self, file_id: str) -> SysFile:
        """按主键查询文件元数据，不存在时抛出 NotFoundError。"""
        entity = await self.get_by_id(file_id)
        if entity is None:
            raise NotFoundError("File not found")
        return entity

    async def update(self, payload: FileUpdateRequest) -> None:
        """更新文件的原始文件名。"""
        entity = await self.get_required(payload.id)
        entity.original_name = payload.original_name
        await self.db.flush()

    async def list_by_ids(self, file_ids: list[str]) -> list[SysFile]:
        """按 ID 列表批量查询文件元数据。"""
        unique_ids = list(dict.fromkeys(file_ids))
        stmt = select(SysFile).where(SysFile.id.in_(unique_ids))
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_by_object_names(self, object_names: list[str]) -> list[SysFile]:
        """按对象名列表批量查询文件元数据。"""
        unique_names = list(dict.fromkeys(object_names))
        if not unique_names:
            return []
        stmt = select(SysFile).where(SysFile.object_name.in_(unique_names))
        return list((await self.db.execute(stmt)).scalars().all())

    async def delete_many(self, file_ids: list[str]) -> None:
        """按 ID 列表批量删除文件元数据。"""
        unique_ids = list(dict.fromkeys(file_ids))
        await self.db.execute(delete(SysFile).where(SysFile.id.in_(unique_ids)))

    async def list_files(
        self,
        query: FileAdminPageQuery,
        data_scope_filter: ColumnElement[bool] | None = None,
    ) -> tuple[list[SysFile], int]:
        """分页查询文件元数据列表。"""
        stmt: Select[tuple[SysFile]] = select(SysFile)
        count_stmt = select(func.count(SysFile.id))
        filters = []
        if query.original_name:
            filters.append(ci_like(SysFile.original_name, query.original_name))
        if query.object_name:
            filters.append(ci_like(SysFile.object_name, query.object_name))
        if query.storage_provider:
            filters.append(SysFile.storage_provider == query.storage_provider)
        if query.content_type:
            filters.append(ci_like(SysFile.content_type, query.content_type))
        if data_scope_filter is not None:
            filters.append(data_scope_filter)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysFile.created_at.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def delete(self, entity: SysFile) -> None:
        """删除文件元数据记录，物理文件删除由服务层协调。"""
        await self.db.delete(entity)
