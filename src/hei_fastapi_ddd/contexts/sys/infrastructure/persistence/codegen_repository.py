"""代码生成仓储层：方案/字段的持久化、数据库元数据内省与资源选项查询。"""

from collections.abc import Mapping
from typing import Any

from sqlalchemy import Select, delete, func, inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.domain.enums import ResourceType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import (
    SysResource,
    SysResourceModule,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.codegen_po import (
    SysCodegenField,
    SysCodegenPlan,
)
from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum
from hei_fastapi_ddd.shared.persistence.compat import ci_like
from hei_fastapi_ddd.types.business import ConflictError, NotFoundError


def _row_plan(entity: SysCodegenPlan) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


def _row_field(entity: SysCodegenField) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


def _row_resource(entity: SysResource) -> dict[str, Any]:
    mapper = inspect(entity).mapper
    return {attr.key: getattr(entity, attr.key) for attr in mapper.column_attrs}


class CodegenRepositoryImpl:
    """代码生成仓储。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Mapping[str, Any]) -> dict[str, Any]:
        await self._ensure_plan_name_unique(str(data["name"]))
        payload = dict(data)
        if not payload.get("id"):
            payload.pop("id", None)
        entity = SysCodegenPlan(**payload)
        self.db.add(entity)
        await self.db.flush()
        return _row_plan(entity)

    async def get_by_id(self, plan_id: str) -> dict[str, Any] | None:
        entity = await self.db.get(SysCodegenPlan, plan_id)
        return _row_plan(entity) if entity is not None else None

    async def get_required(self, plan_id: str) -> dict[str, Any]:
        row = await self.get_by_id(plan_id)
        if row is None:
            raise NotFoundError("Codegen plan not found")
        return row

    async def update(self, plan_id: str, data: Mapping[str, Any]) -> None:
        entity = await self.db.get(SysCodegenPlan, plan_id)
        if entity is None:
            raise NotFoundError("Codegen plan not found")
        await self._ensure_plan_name_unique(str(data.get("name", entity.name)), plan_id)
        for key, value in dict(data).items():
            if key != "id":
                setattr(entity, key, value)
        await self.db.flush()

    async def delete_many(self, plan_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(plan_ids))
        if not unique_ids:
            return
        await self.db.execute(
            delete(SysCodegenField).where(SysCodegenField.plan_id.in_(unique_ids))
        )
        await self.db.execute(delete(SysCodegenPlan).where(SysCodegenPlan.id.in_(unique_ids)))

    async def page_admin(
        self,
        filters: Mapping[str, Any],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        stmt: Select[tuple[SysCodegenPlan]] = select(SysCodegenPlan)
        count_stmt = select(func.count(SysCodegenPlan.id))
        clauses = []
        if filters.get("name"):
            clauses.append(ci_like(SysCodegenPlan.name, str(filters["name"])))
        if filters.get("table_name"):
            clauses.append(ci_like(SysCodegenPlan.table_name, str(filters["table_name"])))
        if filters.get("gen_type"):
            clauses.append(SysCodegenPlan.gen_type == filters["gen_type"])
        if clauses:
            stmt = stmt.where(*clauses)
            count_stmt = count_stmt.where(*clauses)
        stmt = (
            stmt.order_by(SysCodegenPlan.updated_at.desc(), SysCodegenPlan.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = [_row_plan(e) for e in (await self.db.execute(stmt)).scalars().all()]
        total = (await self.db.execute(count_stmt)).scalar_one()
        return items, total

    async def list_fields(
        self, plan_id: str, table_role: str | None = None
    ) -> list[dict[str, Any]]:
        await self.get_required(plan_id)
        stmt = select(SysCodegenField).where(SysCodegenField.plan_id == plan_id)
        if table_role:
            stmt = stmt.where(SysCodegenField.table_role == table_role)
        stmt = stmt.order_by(
            SysCodegenField.table_role.asc(), SysCodegenField.sort.asc(), SysCodegenField.id.asc()
        )
        return [_row_field(e) for e in (await self.db.execute(stmt)).scalars().all()]

    async def replace_fields(self, plan_id: str, fields: list[Mapping[str, Any]]) -> None:
        await self.get_required(plan_id)
        await self.db.execute(delete(SysCodegenField).where(SysCodegenField.plan_id == plan_id))
        for item in fields:
            data = dict(item)
            data.pop("id", None)
            self.db.add(SysCodegenField(plan_id=plan_id, **data))
        await self.db.flush()

    async def upsert_reflected_fields(
        self,
        plan_id: str,
        table_role: str,
        fields: list[Mapping[str, Any]],
    ) -> None:
        await self.get_required(plan_id)
        existing_pos = {
            f.column_name: f
            for f in (
                await self.db.execute(
                    select(SysCodegenField).where(
                        SysCodegenField.plan_id == plan_id,
                        SysCodegenField.table_role == table_role,
                    )
                )
            )
            .scalars()
            .all()
        }
        for item in fields:
            data = dict(item)
            data.pop("id", None)
            column_name = data["column_name"]
            entity = existing_pos.get(column_name)
            if entity is None:
                self.db.add(SysCodegenField(plan_id=plan_id, **data))
                continue
            for key, value in data.items():
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

    async def list_resource_options(self, module_id: str | None = None) -> list[dict[str, Any]]:
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
        return [_row_resource(e) for e in (await self.db.execute(stmt)).scalars().all()]

    async def _ensure_plan_name_unique(self, name: str, plan_id: str | None = None) -> None:
        stmt = select(SysCodegenPlan.id).where(SysCodegenPlan.name == name)
        if plan_id:
            stmt = stmt.where(SysCodegenPlan.id != plan_id)
        if (await self.db.execute(stmt)).scalar_one_or_none() is not None:
            raise ConflictError("Codegen plan name already exists")

    async def list_database_tables(self) -> list[dict[str, str | None]]:
        async with self.db.bind.connect() as conn:  # type: ignore[union-attr]
            return await conn.run_sync(_inspect_tables)

    async def list_database_columns(self, table_name: str) -> list[dict[str, Any]]:
        async with self.db.bind.connect() as conn:  # type: ignore[union-attr]
            columns = await conn.run_sync(_inspect_columns, table_name)
        if not columns:
            raise NotFoundError("Database table not found")
        return columns


EXCLUDED_TABLES = {"alembic_version", "sys_codegen_plan", "sys_codegen_field"}


def _inspect_tables(conn: Connection) -> list[dict[str, str | None]]:
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
