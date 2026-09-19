"""角色 HTTP 组装。"""

from __future__ import annotations

from hei_fastapi_ddd.contexts.iam.api.role_schemas import (
    RoleOwnClientResourceResponse,
    RoleOwnResourceResponse,
    RoleOwnUserResponse,
    RoleResourceGrantInfo,
    SysRoleSchema,
)
from hei_fastapi_ddd.contexts.iam.trigger.assembler.account_assembler import AccountAssembler
from hei_fastapi_ddd.shared.schema.base import to_schema, to_schema_list
from hei_fastapi_ddd.shared.web.pagination import PageData


def to_role_schema(row: dict) -> SysRoleSchema:
    return to_schema(SysRoleSchema, row)


def to_role_schema_page(rows: list[dict]) -> list[SysRoleSchema]:
    return to_schema_list(SysRoleSchema, rows)


def to_role_page(data: PageData[dict]) -> PageData[SysRoleSchema]:
    return PageData(
        current=data.current,
        size=data.size,
        total=data.total,
        records=to_role_schema_page(list(data.records)),
    )


def to_own_resource(view: dict) -> RoleOwnResourceResponse:
    return RoleOwnResourceResponse(
        id=view["id"],
        modules=view["modules"],
        grant_info_list=[
            RoleResourceGrantInfo.model_validate(g) for g in view.get("grant_info_list") or []
        ],
    )


def to_own_client_resource(view: dict) -> RoleOwnClientResourceResponse:
    return RoleOwnClientResourceResponse(
        id=view["id"],
        modules=view["modules"],
        grant_info_list=[
            RoleResourceGrantInfo.model_validate(g) for g in view.get("grant_info_list") or []
        ],
    )


async def to_own_user(assembler: AccountAssembler, view: dict) -> RoleOwnUserResponse:
    users = await assembler.build_account_picker_schemas(view.get("users") or [])
    return RoleOwnUserResponse(
        id=view["id"],
        users=users,
        account_ids=list(view.get("account_ids") or []),
    )
