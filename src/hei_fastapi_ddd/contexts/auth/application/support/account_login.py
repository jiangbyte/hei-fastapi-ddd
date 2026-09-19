"""Author: Charlie

账户登录名解析：基于 AccountApi，避免依赖 sys/iam 基础设施。
"""

from __future__ import annotations

from hei_fastapi_ddd.contexts.iam.application.api.account_api import AccountApi
from hei_fastapi_ddd.contexts.sys.application.audit.support import resolve_account_login


class _AccountIdentityReader:
    """适配 AccountApi 为 sys 审计只读端口。"""

    def __init__(self, account_api: AccountApi):
        self._account_api = account_api

    async def list_identities_by_account_ids(self, account_ids: list[str]):
        return await self._account_api.list_identities_by_account_ids(account_ids)


async def resolve_account_login_label(account_api: AccountApi, account_id: str | None) -> str | None:
    """解析账户主登录名。"""
    return await resolve_account_login(_AccountIdentityReader(account_api), account_id)
