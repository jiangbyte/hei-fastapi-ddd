"""代码生成服务层：方案维护、数据库内省、字段同步与预览下载。"""

from __future__ import annotations

from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.application.codegen.dto import (
    CodegenFieldsQuery,
    CodegenFieldsUpdateBatchCommand,
    CodegenFieldUpdateItem,
    CodegenIdQuery,
    CodegenIdsCommand,
    CodegenParentResourcesQuery,
    CodegenPlanCreateCommand,
    CodegenPlanPageQuery,
    CodegenPlanUpdateCommand,
    CodegenTableColumnsQuery,
)
from hei_fastapi_ddd.contexts.sys.application.codegen.templates import render_files
from hei_fastapi_ddd.contexts.sys.domain.codegen.repository import CodegenRepository
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.types.business import ConflictError


class CodegenService:
    """代码生成服务，编排方案校验、字段同步与文件渲染。"""

    def __init__(self, db: AsyncSession, repo: CodegenRepository):
        self.db = db
        self.repo = repo

    async def create(self, command: CodegenPlanCreateCommand) -> None:
        """校验表结构后创建方案并同步反射字段。"""
        await self._validate_plan_tables(command)
        async with transactional(self.db):
            plan = await self.repo.create(command.model_dump(exclude_none=True))
            await self._sync_reflected_fields(plan)
            audit_snapshots.created_entity(plan)

    async def update(self, command: CodegenPlanUpdateCommand) -> None:
        """校验表结构后更新方案并重新同步反射字段。"""
        await self._validate_plan_tables(command)
        before = await self.repo.get_required(command.id)
        audit_snapshots.before_entity(before)
        async with transactional(self.db):
            await self.repo.update(
                command.id, command.model_dump(exclude={"id"}, exclude_none=True)
            )
            plan = await self.repo.get_required(command.id)
            await self._sync_reflected_fields(plan)
            audit_snapshots.after_entity(plan)

    async def delete(self, command: CodegenIdsCommand) -> None:
        """事务内批量删除方案。"""
        unique_ids = list(dict.fromkeys(command.ids))
        entities = [
            row
            for entity_id in unique_ids
            if (row := await self.repo.get_by_id(entity_id)) is not None
        ]
        async with transactional(self.db):
            audit_snapshots.deleted_all(entities)
            await self.repo.delete_many(unique_ids)

    async def detail(self, query: CodegenIdQuery) -> dict[str, Any]:
        """查询方案详情。"""
        return await self.repo.get_required(query.id)

    async def page_admin(self, query: CodegenPlanPageQuery) -> PageData[dict[str, Any]]:
        """分页查询方案。"""
        filters = query.model_dump(exclude={"page", "size", "offset"})
        items, total = await self.repo.page_admin(
            filters, offset=query.offset, limit=query.size
        )
        return build_page(query, total, items)

    async def tables(self) -> list[dict[str, str | None]]:
        """列出可生成的数据库表。"""
        return await self.repo.list_database_tables()

    async def table_columns(self, query: CodegenTableColumnsQuery) -> list[dict[str, Any]]:
        """查询指定表的列元数据。"""
        return [
            _column_view(item)
            for item in await self.repo.list_database_columns(query.table_name)
        ]

    async def fields(self, query: CodegenFieldsQuery) -> list[dict[str, Any]]:
        """查询方案的字段配置。"""
        return await self.repo.list_fields(query.plan_id, query.table_role)

    async def update_fields_batch(self, command: CodegenFieldsUpdateBatchCommand) -> None:
        """事务内整体替换方案的字段配置。"""
        before = await self.repo.get_required(command.plan_id)
        audit_snapshots.before_entity(before)
        field_rows = [f.model_dump(exclude={"id"}) for f in command.fields]
        async with transactional(self.db):
            await self.repo.replace_fields(command.plan_id, field_rows)
            after = await self.repo.get_required(command.plan_id)
            audit_snapshots.after_entity(after)

    async def parent_resources(
        self, query: CodegenParentResourcesQuery
    ) -> list[dict[str, Any]]:
        """查询可作为父资源的资源选项树。"""
        return _build_resource_options(await self.repo.list_resource_options(query.module_id))

    async def preview(self, query: CodegenIdQuery) -> dict[str, Any]:
        """渲染方案的文件预览。"""
        plan = await self.repo.get_required(query.id)
        main_fields = await self.repo.list_fields(plan["id"], "MAIN")
        sub_fields = await self.repo.list_fields(plan["id"], "SUB")
        needs_sync = not main_fields or (
            plan.get("gen_type") in {"LEFT_TREE_TABLE", "MASTER_DETAIL"} and not sub_fields
        )
        if needs_sync:
            await self._sync_reflected_fields(plan)
            main_fields = await self.repo.list_fields(plan["id"], "MAIN")
            sub_fields = await self.repo.list_fields(plan["id"], "SUB")
        files = render_files(plan, main_fields, sub_fields)
        return {"files": files}

    async def download(self, query: CodegenIdQuery) -> tuple[bytes, str]:
        """将预览文件打包为 zip。"""
        preview = await self.preview(query)
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_file:
            for file in preview["files"]:
                zip_file.writestr(file.path, file.content)
        return buffer.getvalue(), f"codegen-{query.id}.zip"

    async def _validate_plan_tables(
        self, command: CodegenPlanCreateCommand | CodegenPlanUpdateCommand
    ) -> None:
        """校验方案引用的主表/子表与主键/外键字段确实存在。"""
        main_columns = await self.repo.list_database_columns(command.table_name)
        main_column_names = {column["column_name"] for column in main_columns}
        if command.pk_column not in main_column_names:
            raise ConflictError("Main primary key field does not exist")
        if command.gen_type in {"TREE", "LEFT_TREE_TABLE"}:
            if command.tree_parent_field not in main_column_names:
                raise ConflictError("Tree parent field does not exist")
            if command.tree_label_field not in main_column_names:
                raise ConflictError("Tree label field does not exist")
        if command.gen_type in {"LEFT_TREE_TABLE", "MASTER_DETAIL"}:
            if not command.sub_table or not command.sub_pk or not command.sub_foreign_key:
                raise ConflictError("Sub table configuration is incomplete")
            sub_columns = await self.repo.list_database_columns(command.sub_table)
            sub_column_names = {column["column_name"] for column in sub_columns}
            if command.sub_pk not in sub_column_names:
                raise ConflictError("Sub primary key field does not exist")
            if command.sub_foreign_key not in sub_column_names:
                raise ConflictError("Sub foreign key field does not exist")

    async def _sync_reflected_fields(self, plan: dict[str, Any]) -> None:
        """反射主表（及子表）列并合并写入字段配置。"""
        main_columns = await self.repo.list_database_columns(str(plan["table_name"]))
        await self.repo.upsert_reflected_fields(
            str(plan["id"]),
            "MAIN",
            [_default_field(item, "MAIN").model_dump() for item in main_columns],
        )
        if plan.get("gen_type") in {"LEFT_TREE_TABLE", "MASTER_DETAIL"} and plan.get("sub_table"):
            sub_columns = await self.repo.list_database_columns(str(plan["sub_table"]))
            await self.repo.upsert_reflected_fields(
                str(plan["id"]),
                "SUB",
                [_default_field(item, "SUB").model_dump() for item in sub_columns],
            )


def _column_view(column: dict[str, Any]) -> dict[str, Any]:
    return {
        "column_name": column["column_name"],
        "label": column.get("column_comment"),
        "db_type": column["db_type"],
        "value_type": column["python_type"],
        "ui_type": column["typescript_type"],
        "primary_key": column["is_primary_key"],
        "nullable": column["is_nullable"],
        "max_length": column.get("max_length"),
    }


def _default_field(column: dict[str, Any], table_role: str) -> CodegenFieldUpdateItem:
    column_name = column["column_name"]
    is_pk = bool(column["is_primary_key"])
    is_audit = column_name in {"created_at", "created_by", "updated_at", "updated_by"}
    is_nullable = bool(column["is_nullable"])
    python_type = column["python_type"]
    widget = _default_widget(column_name, python_type)
    return CodegenFieldUpdateItem(
        table_role=table_role,  # type: ignore[arg-type]
        column_name=column_name,
        label=column.get("column_comment"),
        db_type=column["db_type"],
        value_type=python_type,
        ui_type=column["typescript_type"],
        widget=widget,
        dict_code="COMMON_STATUS" if column_name == "status" else None,
        query_operator=_default_query_operator(column_name, python_type),
        in_table=not is_audit,
        in_form=not is_pk and not is_audit,
        in_detail=True,
        in_query=column_name in {"name", "title", "code", "status", "category", "type"},
        primary_key=is_pk,
        required=not is_nullable and not is_pk and not is_audit,
        unique_flag=False,
        nullable=is_nullable,
        max_length=column.get("max_length"),
        sort=int(column.get("sort") or 99),
    )


def _default_widget(column_name: str, python_type: str) -> str:
    if column_name == "status":
        return "dict"
    if python_type in {"int", "float"}:
        return "number"
    if python_type == "bool":
        return "switch"
    if any(keyword in column_name for keyword in ("content", "description", "remark")):
        return "textarea"
    return "input"


def _default_query_operator(column_name: str, python_type: str) -> str | None:
    if column_name == "status" or python_type in {"int", "bool"}:
        return "EQ"
    if column_name in {"name", "title", "code", "category", "type"}:
        return "LIKE"
    return None


def _build_resource_options(resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids = {item["id"] for item in resources}
    node_map: dict[str, dict[str, Any]] = {}
    for item in resources:
        node_map[item["id"]] = {
            "id": item["id"],
            "parent_id": item.get("parent_id"),
            "name": item["name"],
            "resource_type": item["resource_type"],
            "module_id": item.get("module_id"),
            "sort": item.get("sort"),
            "weight": item.get("sort") or 0,
            "children": None,
        }
    roots: list[dict[str, Any]] = []
    for item in resources:
        node = node_map[item["id"]]
        parent_id = item.get("parent_id")
        if parent_id and parent_id in ids:
            parent = node_map[parent_id]
            if parent["children"] is None:
                parent["children"] = []
            parent["children"].append(node)
        else:
            roots.append(node)
    return roots
