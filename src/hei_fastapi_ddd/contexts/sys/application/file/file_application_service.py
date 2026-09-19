""" Author: Charlie

文件服务层：对象存储写入与元数据落库的一致性编排、下载与清理。
"""

import asyncio
import logging
import re
from datetime import UTC, datetime
from pathlib import PurePosixPath
from uuid import uuid4

from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.file.content_disposition import (
    content_disposition_attachment,
)
from hei_fastapi_ddd.contexts.sys.application.file.dto import (
    FileAdminPageQuery,
    FileUpdateCommand,
    FileUploadCommand,
    ObjectNameQuery,
)
from hei_fastapi_ddd.contexts.sys.domain.file.repository import FileRepository
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.observability.metrics import record_file_upload_rejected
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.storage.config import StorageConfig
from hei_fastapi_ddd.shared.storage.manager import get_storage, resolve_storage_config
from hei_fastapi_ddd.shared.storage.url import (
    is_external_url,
    looks_like_presigned_url,
    normalize_object_name,
    to_object_key,
)
from hei_fastapi_ddd.shared.web.pagination import PageData, PageQuery, build_page
from hei_fastapi_ddd.types.business import (
    AuthorizationError,
    BusinessError,
    NotFoundError,
)

logger = logging.getLogger(__name__)


def _is_invalid_public_object_name(object_name: str) -> bool:
    """对象名合法性校验：拒绝 .. 片段、前导 / 与反斜杠。"""
    if not object_name:
        return True
    if object_name.startswith("/") or "\\" in object_name:
        return True
    if any(part in {"", ".", ".."} for part in object_name.split("/")):
        return True
    return False


class FileService:
    """文件服务，负责对象存储写入与文件元数据落库的一致性编排。"""

    def __init__(self, db: AsyncSession, repo: FileRepository) -> None:
        """绑定会话并注入仓储端口。"""
        self.db = db
        self.repo = repo

    def build_object_name(self, filename: str, category: str = "uploads") -> str:
        """构造对象存储路径，按日期分片 + UUID，不暴露原始文件名。"""
        safe_name = PurePosixPath(filename).name
        suffix = PurePosixPath(safe_name).suffix.lower()
        now = datetime.now(UTC)
        category = self._normalize_category(category)
        prefix = f"{category}/" if category else ""
        return f"{prefix}{now:%Y}/{now:%m}/{now:%d}/{uuid4().hex}{suffix}"

    async def upload(self, payload: FileUploadCommand) -> dict:
        """上传文件并创建元数据记录，参数通过对象统一承载。"""
        self._validate_upload(payload)
        storage_config = self._resolve_upload_storage_config(payload)
        storage = self._get_storage(storage_config)
        object_name = payload.object_name or self.build_object_name(
            payload.filename,
            payload.category or "uploads",
        )
        object_name = self._validate_object_name(object_name)
        await asyncio.to_thread(
            storage.upload_bytes,
            object_name,
            payload.content,
            content_type=payload.content_type,
        )
        try:
            async with transactional(self.db):
                entity = await self.repo.create(
                    {
                        "object_name": object_name,
                        "original_name": PurePosixPath(payload.filename).name,
                        "storage_provider": storage_config.provider,
                        "bucket": storage_config.bucket or None,
                        "content_type": payload.content_type,
                        "size": len(payload.content),
                        "url": object_name,
                    }
                )
                audit_snapshots.created_entity(entity)
            return self._with_resolved_url(dict(entity))
        except Exception:
            # 补偿：元数据提交失败时避免孤立对象。
            try:
                await asyncio.to_thread(storage.delete_object, object_name)
            except Exception:
                logger.warning(
                    "Failed to rollback storage object after DB error: %s",
                    object_name,
                    exc_info=True,
                )
            raise

    async def update(self, payload: FileUpdateCommand) -> None:
        """事务内更新文件信息。"""
        entity = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(entity)
        async with transactional(self.db):
            await self.repo.update(payload.id, {"original_name": payload.original_name})
            after = await self.repo.get_required(payload.id)
            audit_snapshots.after_entity(after)

    async def delete(self, ids: list[str]) -> None:
        """按文件 ID 批量删除对象存储文件和文件元数据（对齐 hei-boot）。

        存储删除失败不阻断元数据清理（残留/存储不可达时仍删除库记录），仅记录告警。
        """
        unique_ids = list(dict.fromkeys(ids))
        entities = await self.repo.list_by_ids(unique_ids)
        if not entities:
            return
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            # 对象存储删除为外部 I/O，有界并发避免逐文件串行等待。
            semaphore = asyncio.Semaphore(8)

            async def _delete_object(entity: dict) -> None:
                async with semaphore:
                    try:
                        await asyncio.to_thread(
                            self._get_storage(
                                self._resolve_entity_storage_config(entity)
                            ).delete_object,
                            entity["object_name"],
                        )
                    except Exception as exc:
                        logger.warning(
                            "Failed to delete storage object, skip (id=%s, object=%s, provider=%s): %s",
                            entity.get("id"),
                            entity.get("object_name"),
                            entity.get("storage_provider"),
                            exc,
                        )

            await asyncio.gather(*[_delete_object(entity) for entity in entities])
            await self.repo.delete_many([str(entity["id"]) for entity in entities])

    async def delete_by_object_name(self, object_name: str) -> None:
        """按对象存储路径删除文件和元数据（对齐 hei-boot）。

        未找到或外部 URL 静默返回；存储删除失败仅告警，不阻断元数据清理。
        """
        normalized = normalize_object_name(object_name)
        if not normalized or is_external_url(normalized):
            return
        entity = await self.repo.get_by_object_name(normalized)
        if entity is None:
            return
        audit_snapshots.deleted_entity(entity)
        storage = self._get_storage(self._resolve_entity_storage_config(entity))
        async with transactional(self.db):
            try:
                await asyncio.to_thread(storage.delete_object, normalized)
            except Exception as exc:
                logger.warning(
                    "Failed to delete storage object, skip (id=%s, object=%s, provider=%s): %s",
                    entity.get("id"),
                    entity.get("object_name"),
                    entity.get("storage_provider"),
                    exc,
                )
            await self.repo.delete_by_id(str(entity["id"]))

    async def detail(
        self,
        file_id: str,
        session: SessionPayload | None = None,
    ) -> dict:
        """查询文件详情并解析访问 URL。"""
        entity = await self.repo.get_required(file_id)
        if session is not None:
            self.assert_owned_by_current(entity, session)
        return self._with_resolved_url(dict(entity))

    async def list_by_ids(
        self,
        ids: list[str],
        session: SessionPayload | None = None,
    ) -> list[dict]:
        """按 ID 列表查询文件元数据。"""
        unique_ids = list(dict.fromkeys(ids))
        entities = await self.repo.list_by_ids(unique_ids)
        if session is not None:
            for entity in entities:
                self.assert_owned_by_current(entity, session)
        return [self._with_resolved_url(dict(entity)) for entity in entities]

    async def resolve_access_url(self, value: str | None) -> str | None:
        """解析可浏览器访问的 URL（永久直连或重新签发预签名），对齐 hei-boot resolveAccessUrl。"""
        results = await self.resolve_access_urls([value])
        if not value:
            return None
        raw = str(value).strip()
        return results.get(raw)

    async def resolve_access_urls(self, values: list[str | None]) -> dict[str, str | None]:
        """批量解析访问 URL：查 sys_file 按 storage_provider 签发；无元数据则回退默认引擎。

        返回键为原始入参（strip 后）；无法解析的值为 None。
        """
        result: dict[str, str | None] = {}
        pending_keys: dict[str, list[str]] = {}  # object_key -> raw inputs
        for value in values:
            if value is None:
                continue
            raw = str(value).strip()
            if not raw:
                result[raw] = None
                continue
            if is_external_url(raw) and not looks_like_presigned_url(raw):
                result[raw] = raw
                continue
            key = to_object_key(raw) if is_external_url(raw) else normalize_object_name(raw)
            if not key or is_external_url(key):
                result[raw] = raw if is_external_url(raw) else None
                continue
            pending_keys.setdefault(key, []).append(raw)

        if not pending_keys:
            return result

        entities = await self.repo.list_by_object_names(list(pending_keys.keys()))
        entity_by_key = {entity["object_name"]: entity for entity in entities}

        for key, raws in pending_keys.items():
            entity = entity_by_key.get(key)
            try:
                storage = self._get_storage(self._resolve_entity_storage_config(entity))
                resolved = str(storage.get_object_url(key))
            except Exception:
                logger.warning(
                    "Failed to resolve file URL | key=%s provider=%s",
                    key,
                    entity.get("storage_provider") if entity else None,
                    exc_info=True,
                )
                resolved = None
            for raw in raws:
                result[raw] = resolved
        return result

    async def scrub_persisted_presigned_urls(self) -> int:
        """将库内疑似预签名的 sys_file.url 刷回 object_name。"""
        return await self.repo.scrub_persisted_presigned_urls()

    async def download_by_id(
        self,
        file_id: str,
        session: SessionPayload | None = None,
    ) -> Response:
        """按 ID 下载文件（传入 session 时校验归属）。"""
        entity = await self.repo.get_required(file_id)
        if session is not None:
            self.assert_owned_by_current(entity, session)
        return await self.response(ObjectNameQuery(object_name=str(entity["object_name"])))

    async def get_url(
        self,
        query: ObjectNameQuery,
        session: SessionPayload | None = None,
    ) -> str:
        """优先返回已落库的稳定 URL，不存在时退化为存储层实时构造。"""
        normalized = normalize_object_name(query.object_name)
        if not normalized:
            raise NotFoundError("File not found")
        if is_external_url(normalized) and not looks_like_presigned_url(normalized):
            return normalized
        key = to_object_key(normalized) if is_external_url(normalized) else normalized
        if not key:
            raise NotFoundError("File not found")
        entity = await self.repo.get_by_object_name(key)
        if session is not None:
            self.assert_owned_by_current(entity, session)
        storage = self._get_storage(self._resolve_entity_storage_config(entity))
        return str(storage.get_object_url(key))

    async def get_presigned_url(
        self,
        query: ObjectNameQuery,
        session: SessionPayload | None = None,
    ) -> str:
        """获取对象的签名访问地址。"""
        normalized = normalize_object_name(query.object_name)
        if not normalized:
            raise NotFoundError("File not found")
        if is_external_url(normalized) and not looks_like_presigned_url(normalized):
            return normalized
        key = to_object_key(normalized) if is_external_url(normalized) else normalized
        if not key:
            raise NotFoundError("File not found")
        entity = await self.repo.get_by_object_name(key)
        if session is not None:
            self.assert_owned_by_current(entity, session)
        storage = self._get_storage(self._resolve_entity_storage_config(entity))
        return str(storage.get_presigned_url(key))

    async def response(self, query: ObjectNameQuery) -> Response:
        """按对象名流式返回文件内容（鉴权下载），带 RFC5987 Content-Disposition。"""
        normalized = normalize_object_name(query.object_name)
        if not normalized or is_external_url(normalized):
            raise NotFoundError("File not found")
        if _is_invalid_public_object_name(query.object_name):
            raise BusinessError("Invalid object_name")
        entity = await self.repo.get_by_object_name(normalized)
        if entity is None:
            raise NotFoundError("File not found")
        storage = self._get_storage(self._resolve_entity_storage_config(entity))
        try:
            content = await asyncio.to_thread(storage.get_object_bytes, normalized)
        except Exception as exc:
            raise NotFoundError("File not found") from exc
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": content_disposition_attachment(str(entity["original_name"])),
            },
        )

    async def page(
        self,
        query: FileAdminPageQuery | PageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[dict]:
        """分页列出文件元数据记录。"""
        page_query = (
            query
            if isinstance(query, FileAdminPageQuery)
            else FileAdminPageQuery(current=query.current, size=query.size)
        )
        items, total = await self.repo.page_admin(
            page_query.model_dump(exclude={"current", "size"}),
            offset=page_query.offset,
            limit=page_query.size,
            session=session,
        )
        records = [self._with_resolved_url(dict(item)) for item in items]
        return build_page(page_query, total, records)  # type: ignore[arg-type]

    def assert_owned_by_current(
        self,
        entity: dict | None,
        session: SessionPayload,
    ) -> None:
        """校验文件归属当前账户。"""
        if entity is None:
            raise NotFoundError("File not found")
        if str(entity.get("created_by")) != str(session.account_id):
            raise AuthorizationError("无权访问该文件")

    def _with_resolved_url(self, row: dict) -> dict:
        """按存储配置解析并回填文件的访问 URL。"""
        storage_config = resolve_storage_config(provider=row.get("storage_provider"))
        resolved_url = self._get_storage(storage_config).get_object_url(str(row["object_name"]))
        row["url"] = str(resolved_url) or row.get("url")
        return row

    def _resolve_upload_storage_config(self, payload: FileUploadCommand) -> StorageConfig:
        """根据上传请求解析目标存储配置。"""
        return resolve_storage_config(provider=payload.storage_provider)

    def _resolve_entity_storage_config(self, entity: dict | None) -> StorageConfig:
        """根据文件记录解析其存储配置，无记录时回退默认。"""
        if entity is None:
            return resolve_storage_config()
        return resolve_storage_config(provider=entity.get("storage_provider"))

    def _get_storage(self, config: StorageConfig):
        """按配置获取存储实现。"""
        return get_storage(config.id)

    def _validate_upload(self, payload: FileUploadCommand) -> None:
        """校验上传文件的扩展名、类型、大小与分类。"""
        safe_name = PurePosixPath(payload.filename).name
        logger.info(
            "upload validation | filename=%s suffix=%s "
            "allowed_extensions=%s denied_extensions=%s "
            "content_type=%s allowed_content_types=%s",
            payload.filename,
            PurePosixPath(safe_name).suffix.lower(),
            settings.storage.upload_allowed_extensions,
            settings.storage.upload_denied_extensions,
            payload.content_type,
            settings.storage.upload_allowed_content_types,
        )
        suffix = PurePosixPath(safe_name).suffix.lower()
        if not safe_name or safe_name in {".", ".."}:
            self._reject_upload("invalid_filename", "Invalid filename")
        if len(payload.content) > settings.storage.upload_max_bytes:
            self._reject_upload("too_large", "File is too large")
        denied_extensions = {item.lower() for item in settings.storage.upload_denied_extensions}
        if suffix and suffix in denied_extensions:
            self._reject_upload("denied_extension", "File extension is not allowed")
        allowed_extensions = {
            item.lower() for item in settings.storage.upload_allowed_extensions if item
        }
        if allowed_extensions and suffix not in allowed_extensions:
            self._reject_upload("extension_not_allowed", "File extension is not allowed")
        allowed_content_types = {
            item.lower() for item in settings.storage.upload_allowed_content_types if item
        }
        if allowed_content_types and payload.content_type.lower() not in allowed_content_types:
            self._reject_upload("content_type_not_allowed", "File content type is not allowed")
        self._validate_content_magic_bytes(payload)
        self._normalize_category(payload.category)
        if payload.object_name:
            self._validate_object_name(payload.object_name)

    def _validate_content_magic_bytes(self, payload: FileUploadCommand) -> None:
        """校验文件内容 magic bytes 是否与声明的 content type 一致。

        仅检查下方注册表中有已知 magic 签名的 content type。
        配置表 (``upload_allowed_content_types``) 中明确允许但*无*注册
        magic 签名的类型将静默跳过 — 以兼容自定义/未来类型并避免误报。
        """
        content = getattr(payload, "content", None)
        if not content or not isinstance(content, (bytes, bytearray)):
            return
        if len(content) < 12:
            return
        header = content[:12]

        # 注册表：(magic_prefix, content_type_prefix)
        magic_registry: dict[str, bytes] = {
            "image/jpeg": b"\xff\xd8\xff",
            "image/png": b"\x89PNG\r\n\x1a\n",
            "image/gif": b"GIF",
            "image/webp": b"RIFF",
            "application/pdf": b"%PDF",
        }

        ct = (payload.content_type or "").lower()

        # 在注册表中查找匹配的 content-type 前缀
        known_prefix = None
        for ctype_prefix in magic_registry:
            if ct.startswith(ctype_prefix):
                known_prefix = ctype_prefix
                break

        if known_prefix is None:
            # 该 content-type 在注册表中没有魔数规则 → 跳过检查
            return

        expected_magic = magic_registry[known_prefix]
        if not header.startswith(expected_magic):
            self._reject_upload(
                "content_magic_mismatch",
                f"文件内容类型与声明不符（期望 {payload.content_type}）",
            )

    def _normalize_category(self, category: str) -> str:
        """校验并规范化上传分类路径。"""
        value = str(category or "").strip().strip("/")
        if not value:
            return ""
        if len(value) > settings.storage.upload_category_max_length:
            self._reject_upload("invalid_category", "Upload category is too long")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/_-]*", value):
            self._reject_upload("invalid_category", "Upload category is invalid")
        if any(part in {"", ".", ".."} for part in value.split("/")):
            self._reject_upload("invalid_category", "Upload category is invalid")
        return value

    def _validate_object_name(self, object_name: str) -> str:
        """校验并规范化对象名。"""
        normalized = normalize_object_name(object_name)
        if not normalized or is_external_url(normalized):
            self._reject_upload("invalid_object_name", "Object name is invalid")
        if any(part in {"", ".", ".."} for part in normalized.split("/")):
            self._reject_upload("invalid_object_name", "Object name is invalid")
        return normalized

    def _reject_upload(self, reason: str, message: str) -> None:
        """记录拒绝指标并抛出业务错误。"""
        record_file_upload_rejected(reason)
        raise BusinessError(message)
