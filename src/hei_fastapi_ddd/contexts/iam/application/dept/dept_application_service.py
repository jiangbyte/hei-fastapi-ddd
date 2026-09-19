"""Author: Charlie

部门应用服务：依赖 domain 仓储端口，不依赖 infrastructure / api。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.dept.dto import (
    DeptCreateCommand,
    DeptPageQuery,
    DeptUpdateCommand,
)
from hei_fastapi_ddd.contexts.iam.domain.dept.repository import DeptRepository
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest
from hei_fastapi_ddd.shared.security.data_scope import IAM_DEPT_PAGE, resolve_data_scope_dept_ids
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import AuthorizationError


class DeptService:
    """部门应用服务。"""

    def __init__(
        self,
        db: AsyncSession,
        repo: DeptRepository,
    ):
        self.db = db
        self.repo = repo

    async def create(
        self,
        command: DeptCreateCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """创建部门，传入 session 时校验父级部门可见性。"""
        # 1. 父级须在可见部门集合内
        if session is not None and command.parent_id:
            await self._ensure_dept_ids_visible(session, "iam:dept:create", [command.parent_id])
        # 2. 持久化并写审计
        async with transactional(self.db):
            row = await self.repo.create(command.model_dump())
        audit_snapshots.created_entity(row)

    async def update(
        self,
        command: DeptUpdateCommand,
        session: SessionPayload | None = None,
    ) -> None:
        """更新部门，传入 session 时校验目标及父级可见性。"""
        # 1. 可见性校验
        if session is not None:
            await self._ensure_dept_records_visible(session, "iam:dept:update", [command.id])
            if command.parent_id:
                await self._ensure_dept_records_visible(
                    session, "iam:dept:update", [command.parent_id]
                )
        # 2. 审计前快照、更新、审计后快照
        existing = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(existing)
        async with transactional(self.db):
            await self.repo.update(command.id, command.model_dump(exclude={"id"}))
            updated = await self.repo.get_required(command.id)
        audit_snapshots.after_entity(updated)

    async def delete(
        self,
        payload: IdsRequest,
        session: SessionPayload | None = None,
    ) -> None:
        """删除部门，传入 session 时先校验可见性。"""
        if session is not None:
            await self._ensure_dept_records_visible(session, "iam:dept:delete", payload.ids)
        entities = await self.repo.list_by_ids(payload.ids)
        audit_snapshots.deleted_all(entities)
        async with transactional(self.db):
            await self.repo.delete_many(payload.ids)

    async def detail(
        self,
        query: IdQuery,
        session: SessionPayload | None = None,
    ) -> dict:
        """查询部门详情行（含名称回显字段）。"""
        if session is not None:
            await self._ensure_dept_records_visible(session, "iam:dept:detail", [query.id])
        row = await self.repo.get_required(query.id)
        return (await self._enrich_rows([row]))[0]

    async def page_admin(
        self,
        query: DeptPageQuery,
        session: SessionPayload | None = None,
    ) -> PageData[dict]:
        """分页查询部门，叠加数据范围过滤。"""
        items, total = await self.repo.page_admin(
            query.model_dump(exclude={"current", "size"}),
            offset=query.offset,
            limit=query.size,
            session=session,
        )
        enriched = await self._enrich_rows(items)
        return build_page(query, total, enriched)  # type: ignore[arg-type]

    async def list_dept_tree(self, session: SessionPayload | None = None) -> list[dict]:
        """返回部门树行（嵌套 children）。"""
        # 1. 加载树结构
        raw_records = await self.repo.get_dept_tree(session=session)
        # 2. 批量回显负责人名称
        all_ids: set[str] = set()

        def collect_ids(nodes: Sequence[Mapping[str, object]]) -> None:
            for node in nodes:
                if node.get("master_id"):
                    all_ids.add(str(node["master_id"]))
                if node.get("deputy_master_id"):
                    all_ids.add(str(node["deputy_master_id"]))
                children = node.get("children")
                if isinstance(children, list):
                    collect_ids(children)

        collect_ids(raw_records)
        if all_ids:
            name_map = await self.repo.resolve_account_names(list(all_ids))

            def apply_names(nodes: list[dict]) -> None:
                for node in nodes:
                    mid = node.get("master_id")
                    if mid and str(mid) in name_map:
                        node["master_name"] = name_map[str(mid)]
                    did = node.get("deputy_master_id")
                    if did and str(did) in name_map:
                        node["deputy_master_name"] = name_map[str(did)]
                    children = node.get("children")
                    if isinstance(children, list):
                        apply_names(children)

            apply_names(raw_records)
        return raw_records

    async def _enrich_rows(self, rows: list[dict]) -> list[dict]:
        """批量回显负责人与父级部门名称。"""
        account_ids: set[str] = set()
        parent_ids: set[str] = set()
        for row in rows:
            if row.get("master_id"):
                account_ids.add(str(row["master_id"]))
            if row.get("deputy_master_id"):
                account_ids.add(str(row["deputy_master_id"]))
            if row.get("parent_id"):
                parent_ids.add(str(row["parent_id"]))
        account_map = (
            await self.repo.resolve_account_names(list(account_ids)) if account_ids else {}
        )
        dept_map = await self.repo.resolve_dept_names(list(parent_ids)) if parent_ids else {}
        enriched: list[dict] = []
        for row in rows:
            item = dict(row)
            mid = item.get("master_id")
            if mid and str(mid) in account_map:
                item["master_name"] = account_map[str(mid)]
            did = item.get("deputy_master_id")
            if did and str(did) in account_map:
                item["deputy_master_name"] = account_map[str(did)]
            pid = item.get("parent_id")
            if pid and str(pid) in dept_map:
                item["parent_name"] = dept_map[str(pid)]
            enriched.append(item)
        return enriched

    async def _ensure_dept_records_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        dept_ids: list[str],
    ) -> None:
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return
        if await self.repo.count_depts_in_scope(
            unique_ids, session=session, permission=permission_key
        ) != len(unique_ids):
            raise AuthorizationError("Dept is outside current data scope")

    async def _ensure_dept_ids_visible(
        self,
        session: SessionPayload,
        permission_key: str,
        dept_ids: list[str],
    ) -> None:
        _ = permission_key
        unique_ids = list(dict.fromkeys(dept_ids))
        if not unique_ids:
            return
        visible_dept_ids = await resolve_data_scope_dept_ids(self.db, session, IAM_DEPT_PAGE)
        if visible_dept_ids is None:
            return
        allowed_ids = set(visible_dept_ids)
        if any(dept_id not in allowed_ids for dept_id in unique_ids):
            raise AuthorizationError("Dept is outside current data scope")
