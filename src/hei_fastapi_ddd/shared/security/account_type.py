""" Author: Charlie

账户类型访问控制：校验当前账户类型是否在允许范围内。
"""

from collections.abc import Iterable

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.exceptions.business import AuthorizationError


def assert_account_type_allowed(
    actual_account_type: str,
    expected_account_types: Iterable[AccountType],
) -> None:
    """校验当前账户类型是否在允许访问的枚举范围内。"""
    if actual_account_type not in {account_type.value for account_type in expected_account_types}:
        raise AuthorizationError(f"Account type {actual_account_type!r} is not allowed")
