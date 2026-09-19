""" Author: Charlie

代码生成模板渲染：构建渲染上下文并调用 Jinja2 模板生成前后端源码。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from re import sub
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from hei_fastapi_ddd.contexts.sys.application.codegen.dto import CodegenPreviewFile
from hei_fastapi_ddd.contexts.sys.application.codegen.paths import (
    frontend_api_export_path,
    frontend_api_file_path,
    frontend_api_index_append_path,
    frontend_view_path,
)
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.compat import dialect_name_from_url

AUDIT_COLUMNS = {"created_at", "created_by", "updated_at", "updated_by"}


class _RowView:
    """字典行的属性访问包装，供 Jinja 与字段函数使用。"""

    __slots__ = ("_data",)

    def __init__(self, data: Mapping[str, Any]):
        self._data = dict(data)

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            return self._data[name]
        raise AttributeError(name)


def permission_prefix_key(prefix: str) -> str:
    """生成合法权限前缀：三段式权限码（module:resource:action）段内不允许 - / _。

    代码生成的 require_permission / hasPermission / sys_iam_relation.target_key
    一律使用该函数清洗后的前缀，避免用户输入带 - / _ 的前缀产生非法权限码。
    """
    return sub(r"[-_]", "", prefix or "")
TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "infrastructure" / "codegen" / "template_files"
MENU_PERMISSION_ACTIONS = (
    ("page", "分页", 10),
    ("create", "新增", 20),
    ("detail", "详情", 30),
    ("update", "编辑", 40),
    ("delete", "删除", 50),
    ("tables", "读取数据表", 60),
    ("preview", "预览", 70),
    ("download", "下载", 80),
)
TREE_MENU_PERMISSION_ACTION = ("list", "树列表", 90)


@dataclass(frozen=True)
class RenderContext:
    """模板渲染上下文：封装方案与字段并派生各类路径。"""

    plan: _RowView
    main_fields: list[_RowView]
    sub_fields: list[_RowView]
    generated_at: str

    @property
    def backend_parts(self) -> tuple[str, ...]:
        return tuple(
            python_identifier(part)
            for part in self.plan.module_path.strip("/.").split("/")
            if part.strip()
        )

    @property
    def entity_snake(self) -> str:
        # 实体包名：module_path 最后一段或整段拼成 snake
        parts = self.backend_parts
        return parts[-1] if parts else "entity"

    @property
    def bc_import(self) -> str:
        return "hei_fastapi_ddd.contexts.biz"

    @property
    def module_import(self) -> str:
        # 兼容旧模板：指向 application 实体包
        return f"{self.bc_import}.application.{self.entity_snake}"

    @property
    def module_name(self) -> str:
        return self.entity_snake

    @property
    def backend_dir(self) -> str:
        return f"src/hei_fastapi_ddd/contexts/biz/application/{self.entity_snake}"

    @property
    def api_dir(self) -> str:
        return "src/hei_fastapi_ddd/contexts/biz/api"

    @property
    def domain_dir(self) -> str:
        return f"src/hei_fastapi_ddd/contexts/biz/domain/{self.entity_snake}"

    @property
    def infra_persistence_dir(self) -> str:
        return "src/hei_fastapi_ddd/contexts/biz/infrastructure/persistence"

    @property
    def infra_wiring_path(self) -> str:
        return "src/hei_fastapi_ddd/contexts/biz/infrastructure/wiring.py"

    @property
    def trigger_dir(self) -> str:
        return "src/hei_fastapi_ddd/contexts/biz/trigger/http"

    @property
    def view_path(self) -> str:
        return frontend_view_path(self.plan.component_path)

    @property
    def view_component_dir(self) -> str:
        view_path = PurePosixPath(self.view_path)
        return str(view_path.parent / "components")

    @property
    def child_view_component_dir(self) -> str:
        return str(PurePosixPath(self.view_component_dir) / "children")

    @property
    def api_file(self) -> str:
        return frontend_api_file_path(self.plan.component_path, self.plan.entity_name)

    @property
    def api_export(self) -> str:
        rel = frontend_api_export_path(self.api_file)
        return f"export * as {camel_case(self.plan.entity_name)}Api from '{rel}'"


def render_files(
    plan: Mapping[str, Any],
    main_fields: list[Mapping[str, Any]],
    sub_fields: list[Mapping[str, Any]],
) -> list[CodegenPreviewFile]:
    """根据方案与字段渲染全部生成文件。"""
    plan_view = _RowView(plan)
    ctx = RenderContext(
        plan=plan_view,
        main_fields=[_RowView(item) for item in main_fields],
        sub_fields=[_RowView(item) for item in sub_fields],
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    entity = snake_case(plan_view.entity_name)
    file_specs = [
        (f"{ctx.backend_dir}/__init__.py", "python", "init.py.j2"),
        (f"{ctx.domain_dir}/__init__.py", "python", "init.py.j2"),
        (f"{ctx.domain_dir}/repository.py", "python", "domain_repository.py.j2"),
        (f"{ctx.api_dir}/{entity}_schemas.py", "python", "schema.py.j2"),
        (f"{ctx.backend_dir}/dto.py", "python", "dto.py.j2"),
        (f"{ctx.backend_dir}/{entity}_application_service.py", "python", "service.py.j2"),
        (f"{ctx.infra_persistence_dir}/{entity}_po.py", "python", "model.py.j2"),
        (f"{ctx.infra_persistence_dir}/{entity}_repository.py", "python", "repository.py.j2"),
        (f"{ctx.trigger_dir}/{entity}_router.py", "python", "router.py.j2"),
        (f"{ctx.infra_wiring_path}.append", "python", "wiring.py.j2"),
        (ctx.api_file, "typescript", "api.ts.j2"),
        (frontend_api_index_append_path(), "typescript", "api_index_export.ts.j2"),
        (ctx.view_path, "vue", "index.vue.j2"),
        (f"{ctx.view_component_dir}/ModalForm.vue", "vue", "modal_form.vue.j2"),
        (f"{ctx.view_component_dir}/ModalDetail.vue", "vue", "modal_detail.vue.j2"),
        (
            f"scripts/{snake_case(plan_view.entity_name)}_menu_permission.sql",
            "sql",
            "menu_permission.sql.j2",
        ),
    ]
    if (
        plan_view.gen_type in {"LEFT_TREE_TABLE", "MASTER_DETAIL"}
        and plan_view.sub_entity_name
        and plan_view.sub_table
        and plan_view.sub_pk
    ):
        file_specs.extend(
            [
                (
                    f"{ctx.child_view_component_dir}/ChildModalForm.vue",
                    "vue",
                    "child_modal_form.vue.j2",
                ),
                (
                    f"{ctx.child_view_component_dir}/ChildModalDetail.vue",
                    "vue",
                    "child_modal_detail.vue.j2",
                ),
            ]
        )
    return [
        CodegenPreviewFile(path=path, language=language, content=render_template(template, ctx))
        for path, language, template in file_specs
    ]


def render_template(template_name: str, ctx: RenderContext) -> str:
    """渲染单个模板，构造主表/子表与权限上下文。"""
    env = _environment()
    template = env.get_template(template_name)
    has_tree = ctx.plan.gen_type in {"TREE", "LEFT_TREE_TABLE"}
    has_sub = ctx.plan.gen_type in {"LEFT_TREE_TABLE", "MASTER_DETAIL"}
    main_table_exclude = (
        {ctx.plan.tree_parent_field}
        if ctx.plan.gen_type == "TREE" and ctx.plan.tree_parent_field
        else set()
    )
    main = entity_context(
        ctx.plan.entity_name,
        ctx.plan.table_name,
        ctx.plan.pk_column,
        ctx.main_fields,
        table_exclude=main_table_exclude,
    )
    sub = (
        entity_context(
            ctx.plan.sub_entity_name, ctx.plan.sub_table, ctx.plan.sub_pk, ctx.sub_fields
        )
        if ctx.plan.sub_entity_name and ctx.plan.sub_table and ctx.plan.sub_pk
        else None
    )
    target = sub if template_name.startswith("child_") and sub else main
    has_tree_parent_form = bool(
        has_tree
        and not template_name.startswith("child_")
        and ctx.plan.tree_parent_field
        and any(
            field["name"] == ctx.plan.tree_parent_field for field in main.get("form_fields", [])
        )
    )
    return (
        template.render(
            ctx=ctx,
            plan=ctx.plan,
            main=main,
            sub=sub,
            target=target,
            is_child_template=template_name.startswith("child_"),
            has_tree=has_tree,
            has_tree_parent_form=has_tree_parent_form,
            has_sub=has_sub,
            needs_list_permission=has_tree,
            permission_prefix=permission_prefix_key(ctx.plan.permission_prefix),
            menu_permission=menu_permission_context(has_tree)
            if template_name == "menu_permission.sql.j2"
            else None,
            db_dialect=dialect_name_from_url(settings.db.url),
        ).rstrip()
        + "\n"
    )


def _environment() -> Environment:
    """构建关闭自动转义的 Jinja2 环境并注册过滤器。"""
    # 代码生成输出 Python/TS/Vue 源码而非 HTML — autoescape 会破坏模板。
    env = Environment(  # nosec B701
        loader=FileSystemLoader(TEMPLATE_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        autoescape=False,
    )
    env.filters.update(
        camel=camel_case,
        snake=snake_case,
        sql=sql_str,
        vue_default=vue_default,
        ts_api_name=lambda value: f"{camel_case(value)}Api",
    )
    return env


def entity_context(
    entity_name: str | None,
    table_name: str | None,
    pk_name: str | None,
    fields: list[_RowView],
    table_exclude: set[str] | None = None,
) -> dict[str, Any]:
    """构造实体渲染上下文（模型/表单/查询/表格/详情字段）。"""
    if not entity_name or not table_name or not pk_name:
        return {}
    table_exclude = table_exclude or set()
    model_fields = [
        field_context(field) for field in fields if field.column_name not in AUDIT_COLUMNS
    ]
    form_fields = [field_context(field) for field in fields if is_form_field(field)]
    query_fields = [
        field_context(field) for field in fields if field.in_query and not field.primary_key
    ]
    table_fields = [
        field_context(field)
        for field in fields
        if field.in_table
        and field.column_name not in AUDIT_COLUMNS
        and field.column_name not in table_exclude
    ]
    detail_fields = [
        field_context(field)
        for field in fields
        if field.in_detail and field.column_name not in AUDIT_COLUMNS
    ]
    return {
        "entity_name": entity_name,
        "var_name": camel_case(entity_name),
        "table_name": table_name,
        "pk_name": pk_name,
        "fields": fields,
        "model_fields": model_fields,
        "form_fields": form_fields,
        "query_fields": query_fields,
        "table_fields": table_fields,
        "detail_fields": detail_fields,
        "has_form_datetime": any(field["is_datetime"] for field in form_fields),
        "has_form_json": any(field["is_json"] for field in form_fields),
        "has_form_bool": any(field["is_bool"] for field in form_fields),
        "has_form_int": any(field["python_type"] == "int" for field in form_fields),
        "has_form_float": any(field["python_type"] == "float" for field in form_fields),
        "has_detail_json": any(field["is_json"] for field in detail_fields),
        "has_table_dict": any(field["dict_code"] for field in table_fields),
        "has_query_dict": any(field["dict_code"] for field in query_fields),
        "has_table_bool": any(field["is_bool"] for field in table_fields),
        "has_table_tag": any(field["dict_code"] or field["is_bool"] for field in table_fields),
        "has_detail_dict": any(field["dict_code"] for field in detail_fields),
        "has_detail_bool": any(field["is_bool"] for field in detail_fields),
        "needs_form_normalize": any(
            field["is_datetime"] or field["is_json"] for field in form_fields
        ),
        "needs_submit_normalize": any(
            field["is_datetime"] or field["is_json"] for field in form_fields
        ),
        "uses_wire_bool": any(
            "WireBool" in field["schema_type"] or "WireBool" in field["query_schema_type"]
            for field in (*form_fields, *detail_fields, *query_fields)
        ),
        "uses_wire_int": any(
            "WireInt" in field["schema_type"] or "WireInt" in field["query_schema_type"]
            for field in (*form_fields, *detail_fields, *query_fields)
        ),
        "uses_wire_float": any(
            "WireFloat" in field["schema_type"] or "WireFloat" in field["query_schema_type"]
            for field in (*form_fields, *detail_fields, *query_fields)
        ),
    }


def menu_permission_context(needs_list_permission: bool) -> dict[str, Any]:
    """构造菜单权限 SQL 上下文，含动作与雪花 ID。"""
    actions = list(MENU_PERMISSION_ACTIONS)
    if needs_list_permission:
        actions.append(TREE_MENU_PERMISSION_ACTION)
    return {
        "menu_id": generate_snowflake_id(),
        "actions": [
            {
                "key": key,
                "label": label,
                "sort": sort,
                "resource_id": generate_snowflake_id(),
                "relation_id": generate_snowflake_id(),
            }
            for key, label, sort in actions
        ],
    }


def field_context(field: _RowView) -> dict[str, Any]:
    """将字段配置转为模板所需上下文。"""
    python_type = normalized_py_type(field)
    is_datetime = field.widget == "datetime" or python_type == "datetime"
    is_json = is_json_field(field, python_type)
    return {
        "name": field.column_name,
        "label": field.label or field.column_name,
        "comment": field.label,
        "db_type": field.db_type,
        "python_type": python_type,
        "schema_type": schema_py_type(field),
        "query_schema_type": query_schema_py_type(field),
        "ts_type": field.ui_type,
        "sa_type": sa_type(field),
        "form_widget": field.widget,
        "dict_code": field.dict_code,
        "query_operator": field.query_operator or "LIKE",
        "show_in_table": field.in_table,
        "show_in_form": field.in_form,
        "show_in_detail": field.in_detail,
        "show_in_query": field.in_query,
        "is_primary_key": field.primary_key,
        "is_required": field.required,
        "is_nullable": field.nullable,
        "max_length": field.max_length,
        "default": schema_default(field),
        "vue_default": vue_default(field),
        "is_datetime": is_datetime,
        "is_json": is_json,
        "is_bool": python_type == "bool",
    }


def is_form_field(field: _RowView) -> bool:
    """判断字段是否出现在表单中。"""
    return (
        field.in_form and not field.primary_key and field.column_name not in AUDIT_COLUMNS
    )


def normalized_py_type(field: _RowView) -> str:
    """归一化 Python 类型表示。"""
    if field.value_type == "datetime":
        return "datetime"
    if field.value_type == "dict":
        return "dict[str, Any]"
    return field.value_type


def is_json_field(field: _RowView, python_type: str | None = None) -> bool:
    """判断字段是否为 JSON 类型。"""
    raw_python_type = python_type or normalized_py_type(field)
    return raw_python_type in {"dict", "dict[str, Any]"} or "json" in field.db_type.lower()


def _wire_schema_type(raw: str) -> str:
    """将基础类型映射为 Wire 类型名。"""
    mapping = {"int": "WireInt", "bool": "WireBool", "float": "WireFloat"}
    return mapping.get(raw, raw)


def schema_py_type(field: _RowView) -> str:
    """构造 schema 字段的 Python 类型标注。"""
    raw = _wire_schema_type(normalized_py_type(field))
    if field.nullable and not field.primary_key:
        return f"{raw} | None"
    return raw


def query_schema_py_type(field: _RowView) -> str:
    """构造查询 schema 字段的 Python 类型标注。"""
    raw = _wire_schema_type(normalized_py_type(field))
    if raw.endswith(" | None"):
        return raw
    return f"{raw} | None"


def schema_default(field: _RowView) -> str:
    """推断 schema 字段的默认值表达式。"""
    if field.primary_key or field.required:
        return ""
    if field.value_type in {"dict", "dict[str, Any]"}:
        return " = Field(default_factory=dict)"
    if field.nullable:
        return " = None"
    if field.value_type in {"int", "float"}:
        return " = 0"
    if field.value_type == "bool":
        return " = False"
    return ""


def sa_type(field: _RowView) -> str:
    """将数据库类型映射为 SQLAlchemy 列类型。"""
    raw = field.db_type.lower()
    if "json" in raw:
        return "JSON"
    if "bool" in raw:
        return "Boolean"
    if "date" in raw or "time" in raw:
        return "DateTime(timezone=True)"
    if any(item in raw for item in ("int", "serial")):
        return "Integer"
    if any(item in raw for item in ("numeric", "decimal")):
        return "Numeric"
    if any(item in raw for item in ("float", "double", "real")):
        return "Float"
    if "text" in raw:
        return "Text"
    if field.max_length:
        return f"String({field.max_length})"
    return "String(255)"


def vue_default(field: _RowView | dict[str, Any]) -> str:
    """推断前端表单字段的默认值表达式。"""
    if isinstance(field, dict):
        python_type = field["python_type"]
        form_widget = field["form_widget"]
    else:
        python_type = normalized_py_type(field)
        form_widget = field.widget
    if isinstance(field, dict) and "is_json" in field:
        is_json = field["is_json"]
    elif isinstance(field, _RowView):
        is_json = is_json_field(field)
    else:
        is_json = python_type in {"dict", "dict[str, Any]"}
    if form_widget == "datetime" or python_type == "datetime":
        return "null"
    if python_type in {"int", "float"}:
        return "0"
    if python_type == "bool":
        return "false"
    if is_json:
        return "'{}'"
    return "''"


def snake_case(value: str) -> str:
    """将驼峰/连字符字符串转为 snake_case。"""
    value = sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return value.replace("-", "_").replace(" ", "_").lower().strip("_")


def python_identifier(value: str) -> str:
    """将任意字符串转为合法的 Python 标识符。"""
    value = sub(r"[^0-9a-zA-Z_]", "_", snake_case(value))
    value = sub(r"_+", "_", value).strip("_")
    if not value:
        return "module"
    if value[0].isdigit():
        return f"_{value}"
    return value


def camel_case(value: str) -> str:
    """将字符串转为 camelCase。"""
    snake = snake_case(value)
    head, *tail = snake.split("_")
    return head + "".join(item.capitalize() for item in tail)


def sql_str(value: str | None) -> str:
    """转义并包裹 SQL 字符串字面量，空值返回 NULL。"""
    if value is None or value == "":
        return "NULL"
    return "'" + value.replace("'", "''") + "'"
