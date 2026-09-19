"""账户组 HTTP 组装。"""

from __future__ import annotations

from hei_fastapi_ddd.contexts.iam.api.group_schemas import (
    GroupOwnClientResourceResponse,
    GroupOwnResourceResponse,
    GroupOwnRoleResponse,
    GroupOwnUserResponse,
    GroupResourceGrantInfo,
    SysGroupSchema,
)
from hei_fastapi_ddd.contexts.iam.api.role_schemas import SysRoleSchema
from hei_fastapi_ddd.contexts.iam.trigger.assembler.account_assembler import AccountAssembler
from hei_fastapi_ddd.shared.schema.base import to_schema, to_schema_list
from hei_fastapi_ddd.shared.web.pagination import PageData


def to_group_schema(row: dict) -> SysGroupSchema:
    return to_schema(SysGroupSchema, row)


def to_group_page(data: PageData[dict]) -> PageData[SysGroupSchema]:
    return PageData(
        current=data.current,
        size=data.size,
        total=data.total,
        records=to_schema_list(SysGroupSchema, list(data.records)),
    )


def to_own_role(view: dict) -> GroupOwnRoleResponse:
    return GroupOwnRoleResponse(
        id=view["id"],
        roles=to_schema_list(SysRoleSchema, view.get("roles") or []),
        role_ids=list(view.get("role_ids") or []),
    )


def to_own_resource(view: dict) -> GroupOwnResourceResponse:
    return GroupOwnResourceResponse(
        id=view["id"],
        modules=view["modules"],
        grant_info_list=[
            GroupResourceGrantInfo.model_validate(g) for g in view.get("grant_info_list") or []
        ],
    )


def to_own_client_resource(view: dict) -> GroupOwnClientResourceResponse:
    return GroupOwnClientResourceResponse(
        id=view["id"],
        modules=view["modules"],
        grant_info_list=[
            GroupResourceGrantInfo.model_validate(g) for g in view.get("grant_info_list") or []
        ],
    )


async def to_own_user(assembler: AccountAssembler, view: dict) -> GroupOwnUserResponse:
    users = await assembler.build_account_picker_schemas(view.get("users") or [])
    return GroupOwnUserResponse(
        id=view["id"],
        users=users,
        account_ids=list(view.get("account_ids") or []),
    )
