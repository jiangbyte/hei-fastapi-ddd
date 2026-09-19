"""部门 HTTP 组装。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from hei_fastapi_ddd.contexts.iam.api.dept_schemas import DeptTreeNode, SysDeptSchema
from hei_fastapi_ddd.shared.schema.base import to_schema, to_schema_list


def to_dept_schema(row: dict) -> SysDeptSchema:
    return to_schema(SysDeptSchema, row)


def to_dept_schema_page(rows: list[dict]) -> list[SysDeptSchema]:
    return to_schema_list(SysDeptSchema, rows)


def build_dept_tree_nodes(items: Sequence[Mapping[str, object]]) -> list[DeptTreeNode]:
    nodes: list[DeptTreeNode] = []
    for raw_item in items:
        nodes.append(
            DeptTreeNode(
                id=str(raw_item["id"]),
                name=str(raw_item["name"]),
                category=str(raw_item["category"]),
                parent_id=str(raw_item["parent_id"]) if raw_item.get("parent_id") else None,
                master_id=str(raw_item["master_id"]) if raw_item.get("master_id") else None,
                master_name=str(raw_item["master_name"]) if raw_item.get("master_name") else None,
                deputy_master_id=str(raw_item["deputy_master_id"])
                if raw_item.get("deputy_master_id")
                else None,
                deputy_master_name=str(raw_item["deputy_master_name"])
                if raw_item.get("deputy_master_name")
                else None,
                status=str(raw_item.get("status", "ENABLED")),
                sort=int(raw_item.get("sort", 99)),
                weight=int(raw_item.get("weight", raw_item.get("sort", 99))),
                is_virtual=bool(raw_item.get("is_virtual", False)),
                extra=dict(raw_item.get("extra", {})),
                created_at=raw_item["created_at"],
                created_by=str(raw_item["created_by"]) if raw_item.get("created_by") else None,
                updated_at=raw_item.get("updated_at"),
                updated_by=str(raw_item["updated_by"]) if raw_item.get("updated_by") else None,
                children=_build_children(raw_item.get("children", [])),
            )
        )
    return nodes


def _build_children(items: object) -> list[DeptTreeNode] | None:
    if not isinstance(items, list) or not items:
        return None
    nodes = build_dept_tree_nodes(items)
    return nodes or None
