"""代码生成应用层 DTO。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hei_fastapi_ddd.shared.web.pagination import PageQuery

CodegenType = Literal["TABLE", "TREE", "LEFT_TREE_TABLE", "MASTER_DETAIL"]
CodegenTableRole = Literal["MAIN", "SUB"]


class CodegenPlanCreateCommand(BaseModel):
    """创建代码生成方案。"""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    name: str
    gen_type: CodegenType = "TABLE"
    author: str
    description: str | None = None
    table_name: str
    pk_column: str = "id"
    entity_name: str
    module_path: str
    business_name: str
    api_prefix: str
    permission_prefix: str
    resource_module_id: str | None = None
    parent_resource_id: str | None = None
    menu_name: str
    menu_path: str
    component_path: str
    icon: str | None = None
    sort: int = 99
    tree_parent_field: str | None = None
    tree_label_field: str | None = None
    sub_table: str | None = None
    sub_pk: str | None = None
    sub_foreign_key: str | None = None
    sub_entity_name: str | None = None
    sub_business_name: str | None = None

    @field_validator("author")
    @classmethod
    def validate_author(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("author is required")
        return value

    @model_validator(mode="after")
    def validate_codegen_type(self):
        if self.gen_type in {"TREE", "LEFT_TREE_TABLE"}:
            if not self.tree_parent_field:
                raise ValueError("tree_parent_field is required for tree codegen")
            if not self.tree_label_field:
                raise ValueError("tree_label_field is required for tree codegen")
        if self.gen_type in {"LEFT_TREE_TABLE", "MASTER_DETAIL"}:
            if not self.sub_table:
                raise ValueError("sub_table is required for relation codegen")
            if not self.sub_pk:
                raise ValueError("sub_pk is required for relation codegen")
            if not self.sub_foreign_key:
                raise ValueError("sub_foreign_key is required for relation codegen")
            if not self.sub_entity_name:
                raise ValueError("sub_entity_name is required for relation codegen")
            if not self.sub_business_name:
                raise ValueError("sub_business_name is required for relation codegen")
        return self


class CodegenPlanUpdateCommand(CodegenPlanCreateCommand):
    """更新代码生成方案。"""

    id: str


class CodegenPlanPageQuery(PageQuery):
    """方案分页查询。"""

    name: str | None = None
    table_name: str | None = None
    gen_type: CodegenType | None = None


class CodegenFieldUpdateItem(BaseModel):
    """字段配置项。"""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    table_role: CodegenTableRole = "MAIN"
    column_name: str
    label: str | None = None
    db_type: str
    value_type: str = "str"
    ui_type: str = "string"
    widget: str = "input"
    dict_code: str | None = None
    query_operator: str | None = None
    in_table: bool = True
    in_form: bool = True
    in_detail: bool = True
    in_query: bool = False
    primary_key: bool = False
    required: bool = False
    unique_flag: bool = False
    nullable: bool = True
    max_length: int | None = None
    sort: int = 99


class CodegenFieldsUpdateBatchCommand(BaseModel):
    """批量更新字段。"""

    plan_id: str
    fields: list[CodegenFieldUpdateItem] = Field(min_length=1)


class CodegenTableColumnsQuery(BaseModel):
    """表列查询。"""

    table_name: str


class CodegenFieldsQuery(BaseModel):
    """字段查询。"""

    plan_id: str
    table_role: str | None = None


class CodegenParentResourcesQuery(BaseModel):
    """父资源查询。"""

    module_id: str | None = None


class CodegenIdQuery(BaseModel):
    """方案 ID 查询。"""

    id: str


class CodegenIdsCommand(BaseModel):
    """批量方案 ID。"""

    ids: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class CodegenPreviewFile:
    """预览文件（应用层）。"""

    path: str
    language: str
    content: str
