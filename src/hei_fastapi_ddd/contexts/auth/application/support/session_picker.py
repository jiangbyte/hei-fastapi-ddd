"""Author: Charlie

会话管理账户展示字段：基于 AccountApi 标识行，不依赖 IAM trigger assembler。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hei_fastapi_ddd.contexts.iam.application.api.account_api import AccountApi
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType


async def build_account_picker_fields(
    account_api: AccountApi,
    accounts: list[Mapping[str, Any]],
) -> dict[str, dict[str, str | None]]:
    """账户 ID → {account, name}，name 暂与 account 标识一致。"""
    if not accounts:
        return {}
    account_ids = [str(row["id"]) for row in accounts if row.get("id")]
    identities = await account_api.list_identities_by_account_ids(account_ids)
    account_names: dict[str, str] = {}
    for item in identities:
        if item.get("identity_type") != AccountIdentityType.ACCOUNT.value:
            continue
        account_id = str(item.get("account_id") or "")
        identifier = str(item.get("identifier") or "").strip()
        if account_id and identifier and account_id not in account_names:
            account_names[account_id] = identifier
    result: dict[str, dict[str, str | None]] = {}
    for row in accounts:
        account_id = str(row["id"])
        login = account_names.get(account_id) or account_id
        result[account_id] = {"account": login, "name": login}
    return result
