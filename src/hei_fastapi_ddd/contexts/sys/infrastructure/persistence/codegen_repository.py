""" Author: Charlie

代码生成仓储层：方案/字段的持久化、数据库元数据内省与资源选项查询。
"""

from typing import Any

from sqlalchemy import Select, delete, func, inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum
from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.shared.exceptions.business import ConflictError, NotFoundError
from hei_fastapi_ddd.contexts.iam.domain.enums import ResourceType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource, SysResourceModule
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.codegen_po import SysCodegenField, SysCodegenPlan
from hei_fastapi_ddd.contexts.sys.interfaces.http.codegen_schemas import (
    CodegenFieldUpdateItem,
    CodegenPlanCreateRequest,
    CodegenPlanPageQuery,
    CodegenPlanUpdateRequest,
)


class CodegenRepository:
    """代码生成仓储，管理方案与字段，并提供数据库表结构内省。"""

    def __init__(self, db: AsyncSession):
        """绑定数据库会话。"""
        self.db = db

    async def create(self, payload: CodegenPlanCreateRequest) -> SysCodegenPlan:
        """校验方案名唯一后创建方案。"""
        await self._ensure_plan_name_unique(payload.name)
        data = payload.model_dump(exclude_none=True)
        if not data.get("id"):
            data.pop("id", None)
        entity = SysCodegenPlan(**data)
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def get_by_id(self, plan_id: str) -> SysCodegenPlan | None:
        """按主键查询方案，不存在返回 None。"""
        return await self.db.get(SysCodegenPlan, plan_id)

    async def get_required(self, plan_id: str) -> SysCodegenPlan:
        """按主键查询方案，不存在时抛出 NotFoundError。"""
        entity = await self.get_by_id(plan_id)
        if entity is None:
            raise NotFoundError("Codegen plan not found")
        return entity

    async def update(self, payload: CodegenPlanUpdateRequest) -> None:
        """校验方案名唯一后更新方案字段（排除 id）。"""
        entity = await self.get_required(payload.id)
        await self._ensure_plan_name_unique(payload.name, payload.id)
        data = payload.model_dump(exclude={"id"})
        for key, value in data.items():
            setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, plan_ids: list[str]) -> None:
        """批量删除方案及其字段（不存在的 ID 静默跳过，对齐 hei-boot 幂等语义）。"""
        unique_ids = list(dict.fromkeys(plan_ids))
        if not unique_ids:
            return
        # 先删除关联字段再删除方案，避免遗留孤儿记录。
        await self.db.execute(
            delete(SysCodegenField).where(SysCodegenField.plan_id.in_(unique_ids))
        )
        await self.db.execute(delete(SysCodegenPlan).where(SysCodegenPlan.id.in_(unique_ids)))

    async def page_admin(self, query: CodegenPlanPageQuery) -> tuple[list[SysCodegenPlan], int]:
        """按查询条件后台分页，返回记录列表与总数。"""
        stmt: Select[tuple[SysCodegenPlan]] = select(SysCodegenPlan)
        count_stmt = select(func.count(SysCodegenPlan.id))
        filters = []
        if query.name:
            filters.append(ci_like(SysCodegenPlan.name, query.name))
        if query.table_name:
            filters.append(ci_like(SysCodegenPlan.table_name, query.table_name))
        if query.gen_type:
            filters.append(SysCodegenPlan.gen_type == query.gen_type)
        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)
        stmt = (
            stmt.order_by(SysCodegenPlan.updated_at.desc(), SysCodegenPlan.id.desc())
            .offset(query.offset)
            .limit(query.size)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def list_fields(
        self, plan_id: str, table_role: str | None = None
    ) -> list[SysCodegenField]:
        """查询方案的字段配置，可按表角色过滤。"""
        await self.get_required(plan_id)
        stmt = select(SysCodegenField).where(SysCodegenField.plan_id == plan_id)
        if table_role:
            stmt = stmt.where(SysCodegenField.table_role == table_role)
        stmt = stmt.order_by(
            SysCodegenField.table_role.asc(), SysCodegenField.sort.asc(), SysCodegenField.id.asc()
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def replace_fields(self, plan_id: str, fields: list[CodegenFieldUpdateItem]) -> None:
        """先删后插，整体替换方案的字段配置。"""
        await self.get_required(plan_id)
        await self.db.execute(delete(SysCodegenField).where(SysCodegenField.plan_id == plan_id))
        for item in fields:
            data = item.model_dump(exclude={"id"})
            self.db.add(SysCodegenField(plan_id=plan_id, **data))
        await self.db.flush()

    async def upsert_reflected_fields(
        self,
        plan_id: str,
        table_role: str,
        fields: list[CodegenFieldUpdateItem],
    ) -> None:
        """按字段名合并反射结果，仅覆盖基础元数据而保留用户自定义控件配置。"""
        await self.get_required(plan_id)
        existing = {
            field.column_name: field for field in await self.list_fields(plan_id, table_role)
        }
        for item in fields:
            entity = existing.get(item.column_name)
            data = item.model_dump(exclude={"id"})
            if entity is None:
                self.db.add(SysCodegenField(plan_id=plan_id, **data))
                continue
            for key, value in data.items():
                # 跳过显示开关与查询控件等可编辑项，避免覆盖用户调整。
                if key in {
                    "in_table",
                    "in_form",
                    "in_detail",
                    "in_query",
                    "widget",
                    "dict_code",
                    "query_operator",
                }:
                    continue
                setattr(entity, key, value)
        await self.db.flush()

    async def list_resource_options(
        self,
        module_id: str | None = None,
    ) -> list[SysResource]:
        """查询可作为父资源的管理端目录/菜单/页面。"""
        stmt = (
            select(SysResource)
            .join(SysResourceModule, SysResource.module_id == SysResourceModule.id)
            .where(
                SysResourceModule.client == AccountType.ADMIN.value,
                SysResource.status == StatusEnum.ENABLED.value,
                SysResource.resource_type.in_(
                    [ResourceType.CATALOG.value, ResourceType.MENU.value, ResourceType.PAGE.value]
                ),
            )
            .order_by(SysResource.sort.asc(), SysResource.id.asc())
        )
        if module_id:
            stmt = stmt.where(SysResource.module_id == module_id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def _ensure_plan_name_unique(self, name: str, plan_id: str | None = None) -> None:
        """校验方案名唯一（排除自身），重复时抛出 ConflictError。"""
        stmt = select(SysCodegenPlan.id).where(SysCodegenPlan.name == name)
        if plan_id:
            stmt = stmt.where(SysCodegenPlan.id != plan_id)
        if (await self.db.execute(stmt)).scalar_one_or_none() is not None:
            raise ConflictError("Codegen plan name already exists")

    async def list_database_tables(self) -> list[dict[str, str | None]]:
        """通过数据库内省列出可生成的表及其注释。"""
        async with self.db.bind.connect() as conn:  # type: ignore[union-attr]
            return await conn.run_sync(_inspect_tables)

    async def list_database_columns(self, table_name: str) -> list[dict[str, Any]]:
        """通过数据库内省列出表的列元数据，表不存在时抛出 NotFoundError。"""
        async with self.db.bind.connect() as conn:  # type: ignore[union-attr]
            columns = await conn.run_sync(_inspect_columns, table_name)
        if not columns:
            raise NotFoundError("Database table not found")
        return columns


# 代码生成自身的方案/字段表与迁移版本表不参与生成，避免自引用。
EXCLUDED_TABLES = {"alembic_version", "sys_codegen_plan", "sys_codegen_field"}


def _inspect_tables(conn: Connection) -> list[dict[str, str | None]]:
    """同步内省数据库表，返回表名与注释列表（按表名排序）。"""
    inspector = inspect(conn)
    result: list[dict[str, str | None]] = []
    for table_name in inspector.get_table_names():
        if table_name in EXCLUDED_TABLES:
            continue
        try:
            comment = inspector.get_table_comment(table_name).get("text")
        except NotImplementedError:
            comment = None
        result.append({"table_name": table_name, "table_comment": comment})
    return sorted(result, key=lambda item: item["table_name"] or "")


def _inspect_columns(conn: Connection, table_name: str) -> list[dict[str, Any]]:
    """同步内省表列，映射为前端所需元数据。"""
    inspector = inspect(conn)
    table_names = set(inspector.get_table_names())
    if table_name not in table_names:
        return []
    pk_columns = set(inspector.get_pk_constraint(table_name).get("constrained_columns") or [])
    result: list[dict[str, Any]] = []
    for index, column in enumerate(inspector.get_columns(table_name), start=1):
        column_type = column["type"]
        py_type, ts_type = map_db_type(column_type)
        result.append(
            {
                "column_name": column["name"],
                "column_comment": column.get("comment"),
                "db_type": str(column_type),
                "python_type": py_type,
                "typescript_type": ts_type,
                "is_primary_key": column["name"] in pk_columns,
                "is_nullable": bool(column.get("nullable")),
                "max_length": getattr(column_type, "length", None),
                "sort": index,
            }
        )
    return result


def map_db_type(column_type: object) -> tuple[str, str]:
    """将 SQLAlchemy 列类型映射为 Python 与 TypeScript 类型。"""
    raw = str(column_type).lower()
    if any(item in raw for item in ("int", "serial")):
        return "int", "number"
    if any(item in raw for item in ("numeric", "decimal", "float", "double", "real")):
        return "float", "number"
    if "bool" in raw:
        return "bool", "boolean"
    if "date" in raw or "time" in raw:
        return "datetime", "string"
    if "json" in raw:
        return "dict[str, Any]", "Record<string, any>"
    return "str", "string"
