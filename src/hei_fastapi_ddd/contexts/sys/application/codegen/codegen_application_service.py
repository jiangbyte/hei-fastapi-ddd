""" Author: Charlie

代码生成服务层：方案维护、数据库内省、字段同步与预览下载。
"""

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.exceptions.business import ConflictError
from hei_fastapi_ddd.shared.web.pagination import PageData, build_page
from hei_fastapi_ddd.shared.schema.base import IdQuery, IdsRequest, to_schema, to_schema_list
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.codegen_po import SysCodegenPlan
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.codegen_repository import CodegenRepository
from hei_fastapi_ddd.contexts.sys.interfaces.http.codegen_schemas import (
    CodegenFieldsQuery,
    CodegenFieldsUpdateBatchRequest,
    CodegenFieldUpdateItem,
    CodegenParentResourceOption,
    CodegenParentResourcesQuery,
    CodegenPlanCreateRequest,
    CodegenPlanPageQuery,
    CodegenPlanUpdateRequest,
    CodegenPreviewSchema,
    CodegenTableColumnsQuery,
    DatabaseColumnSchema,
    DatabaseTableSchema,
    SysCodegenFieldSchema,
    SysCodegenPlanSchema,
)
from hei_fastapi_ddd.contexts.sys.application.codegen.templates import render_files


class CodegenService:
    """代码生成服务，编排方案校验、字段同步与文件渲染。"""

    def __init__(self, db: AsyncSession):
        """绑定会话并初始化仓储。"""
        self.db = db
        self.repo = CodegenRepository(db)

    async def create(self, payload: CodegenPlanCreateRequest) -> None:
        """校验表结构后创建方案并同步反射字段。"""
        await self._validate_plan_tables(payload)
        async with transactional(self.db):
            plan = await self.repo.create(payload)
            await self._sync_reflected_fields(plan)
            audit_snapshots.created_entity(plan)

    async def update(self, payload: CodegenPlanUpdateRequest) -> None:
        """校验表结构后更新方案并重新同步反射字段。"""
        await self._validate_plan_tables(payload)
        entity = await self.repo.get_required(payload.id)
        audit_snapshots.before_entity(entity)
        async with transactional(self.db):
            await self.repo.update(payload)
            plan = await self.repo.get_required(payload.id)
            await self._sync_reflected_fields(plan)
            audit_snapshots.after_entity(plan)

    async def delete(self, payload: IdsRequest) -> None:
        """事务内批量删除方案。"""
        unique_ids = list(dict.fromkeys(payload.ids))
        entities = [
            entity
            for entity_id in unique_ids
            if (entity := await self.repo.get_by_id(entity_id)) is not None
        ]
        async with transactional(self.db):
            audit_snapshots.deleted_all(entities)
            await self.repo.delete_many(unique_ids)

    async def detail(self, query: IdQuery) -> SysCodegenPlanSchema:
        """查询方案详情。"""
        return to_schema(SysCodegenPlanSchema, await self.repo.get_required(query.id))

    async def page_admin(self, query: CodegenPlanPageQuery) -> PageData[SysCodegenPlanSchema]:
        """分页查询方案。"""
        items, total = await self.repo.page_admin(query)
        return build_page(query, total, to_schema_list(SysCodegenPlanSchema, items))

    async def tables(self) -> list[DatabaseTableSchema]:
        """列出可生成的数据库表。"""
        return [DatabaseTableSchema(**item) for item in await self.repo.list_database_tables()]

    async def table_columns(self, query: CodegenTableColumnsQuery) -> list[DatabaseColumnSchema]:
        """查询指定表的列元数据。"""
        return [
            DatabaseColumnSchema(**_column_schema_data(item))
            for item in await self.repo.list_database_columns(query.table_name)
        ]

    async def fields(self, query: CodegenFieldsQuery) -> list[SysCodegenFieldSchema]:
        """查询方案的字段配置。"""
        return to_schema_list(
            SysCodegenFieldSchema, await self.repo.list_fields(query.plan_id, query.table_role)
        )

    async def update_fields_batch(self, payload: CodegenFieldsUpdateBatchRequest) -> None:
        """事务内整体替换方案的字段配置。"""
        plan = await self.repo.get_required(payload.plan_id)
        audit_snapshots.before_entity(plan)
        async with transactional(self.db):
            await self.repo.replace_fields(payload.plan_id, payload.fields)
            await self.db.refresh(plan)
            audit_snapshots.after_entity(plan)

    async def parent_resources(
        self, query: CodegenParentResourcesQuery
    ) -> list[CodegenParentResourceOption]:
        """查询可作为父资源的资源选项树。"""
        return _build_resource_options(await self.repo.list_resource_options(query.module_id))

    async def preview(self, query: IdQuery) -> CodegenPreviewSchema:
        """渲染方案的文件预览。

        主表无字段，或关联类型（LEFT_TREE_TABLE/MASTER_DETAIL）子表无字段时，
        先反射同步（对齐 hei-boot preview 的补全逻辑）。
        """
        plan = await self.repo.get_required(query.id)
        main_fields = await self.repo.list_fields(plan.id, "MAIN")
        sub_fields = await self.repo.list_fields(plan.id, "SUB")
        needs_sync = not main_fields or (
            plan.gen_type in {"LEFT_TREE_TABLE", "MASTER_DETAIL"} and not sub_fields
        )
        if needs_sync:
            await self._sync_reflected_fields(plan)
            main_fields = await self.repo.list_fields(plan.id, "MAIN")
            sub_fields = await self.repo.list_fields(plan.id, "SUB")
        return CodegenPreviewSchema(files=render_files(plan, main_fields, sub_fields))

    async def download(self, query: IdQuery) -> tuple[bytes, str]:
        """将预览文件打包为 zip 返回内容与文件名。"""
        preview = await self.preview(query)
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_file:
            for file in preview.files:
                zip_file.writestr(file.path, file.content)
        return buffer.getvalue(), f"codegen-{query.id}.zip"

    async def _validate_plan_tables(
        self, payload: CodegenPlanCreateRequest | CodegenPlanUpdateRequest
    ) -> None:
        """校验方案引用的主表/子表与主键/外键字段确实存在。"""
        main_columns = await self.repo.list_database_columns(payload.table_name)
        main_column_names = {column["column_name"] for column in main_columns}
        if payload.pk_column not in main_column_names:
            raise ConflictError("Main primary key field does not exist")
        if payload.gen_type in {"TREE", "LEFT_TREE_TABLE"}:
            if payload.tree_parent_field not in main_column_names:
                raise ConflictError("Tree parent field does not exist")
            if payload.tree_label_field not in main_column_names:
                raise ConflictError("Tree label field does not exist")
        if payload.gen_type in {"LEFT_TREE_TABLE", "MASTER_DETAIL"}:
            if not payload.sub_table or not payload.sub_pk or not payload.sub_foreign_key:
                raise ConflictError("Sub table configuration is incomplete")
            sub_columns = await self.repo.list_database_columns(payload.sub_table)
            sub_column_names = {column["column_name"] for column in sub_columns}
            if payload.sub_pk not in sub_column_names:
                raise ConflictError("Sub primary key field does not exist")
            if payload.sub_foreign_key not in sub_column_names:
                raise ConflictError("Sub foreign key field does not exist")

    async def _sync_reflected_fields(self, plan: SysCodegenPlan) -> None:
        """反射主表（及子表）列并合并写入字段配置。"""
        main_columns = await self.repo.list_database_columns(plan.table_name)
        await self.repo.upsert_reflected_fields(
            plan.id,
            "MAIN",
            [_default_field(item, "MAIN") for item in main_columns],
        )
        if plan.gen_type in {"LEFT_TREE_TABLE", "MASTER_DETAIL"} and plan.sub_table:
            sub_columns = await self.repo.list_database_columns(plan.sub_table)
            await self.repo.upsert_reflected_fields(
                plan.id,
                "SUB",
                [_default_field(item, "SUB") for item in sub_columns],
            )


def _column_schema_data(column: dict) -> dict:
    """从内省列元数据提取响应所需字段。"""
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


def _default_field(column: dict, table_role: str) -> CodegenFieldUpdateItem:
    """根据内省列构造默认字段配置。"""
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
    """按列名与类型推断默认表单控件。"""
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
    """按列名与类型推断默认查询方式。"""
    if column_name == "status" or python_type in {"int", "bool"}:
        return "EQ"
    if column_name in {"name", "title", "code", "category", "type"}:
        return "LIKE"
    return None


def _build_resource_options(resources) -> list[CodegenParentResourceOption]:
    """将资源列表构建为父子树形选项（对齐 hei-boot parentResources）。"""
    ids = {item.id for item in resources}
    node_map = {
        item.id: CodegenParentResourceOption(
            id=item.id,
            parent_id=item.parent_id,
            name=item.name,
            resource_type=item.resource_type,
            module_id=item.module_id,
            sort=getattr(item, "sort", None),
            weight=getattr(item, "sort", None) or 0,
            children=None,
        )
        for item in resources
    }
    roots: list[CodegenParentResourceOption] = []
    for item in resources:
        node = node_map[item.id]
        parent_id = item.parent_id
        if parent_id and parent_id in ids:
            parent = node_map[parent_id]
            if parent.children is None:
                parent.children = []
            parent.children.append(node)
        else:
            roots.append(node)
    return roots
