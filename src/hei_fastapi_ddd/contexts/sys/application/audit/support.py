"""审计辅助：解析操作主体登录名等。"""

from __future__ import annotations

from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.contexts.sys.domain.account_read.repository import AccountIdentityReadPort


async def resolve_account_login(
    reader: AccountIdentityReadPort,
    account_id: str | None,
) -> str | None:
    """按账号 ID 解析主登录名（优先 ACCOUNT 类型标识）。"""
    if not account_id or not str(account_id).strip():
        return None
    identities = await reader.list_identities_by_account_ids([account_id])
    preferred = (
        AccountIdentityType.ACCOUNT.value,
        AccountIdentityType.EMAIL.value,
        AccountIdentityType.PHONE.value,
    )
    for identity_type in preferred:
        for item in identities:
            if item.get("identity_type") == identity_type and str(item.get("identifier") or "").strip():
                return str(item.get("identifier")).strip()
    return None
