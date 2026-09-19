""" Author: Charlie

用户资料批量查询工具（仅依赖 ProfileReadPort，不触达基础设施）。
"""
from __future__ import annotations

from hei_fastapi_ddd.contexts.profile.application.api.profile_read_port import ProfileReadPort
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.types.business import BusinessError


def as_account_type(account_type: AccountType | str) -> AccountType:
    """将账户类型归一化为 AccountType 枚举，非法值抛 BusinessError。"""
    if isinstance(account_type, AccountType):
        return account_type
    try:
        return AccountType(str(account_type))
    except ValueError as exc:
        raise BusinessError(f"Unsupported account type: {account_type}") from exc


async def get_profile(
    read_port: ProfileReadPort,
    account_type: AccountType | str,
    account_id: str,
) -> dict[str, object] | None:
    """按账户类型与 ID 查询资料记录，不存在时返回 None。"""
    at = as_account_type(account_type)
    return await read_port.get_profile_by_account(at.value, account_id)


async def get_profiles_batch(
    read_port: ProfileReadPort,
    account_type: AccountType | str,
    account_ids: list[str],
) -> dict[str, dict[str, object]]:
    """批量查询资料记录，返回以 account_id 为键的字典。"""
    if not account_ids:
        return {}
    at = as_account_type(account_type)
    return await read_port.get_profiles_by_account_ids(at.value, list(dict.fromkeys(account_ids)))
