"""Author: Charlie

IAM 关系仓储端口。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from hei_fastapi_ddd.contexts.iam.domain.enums import GrantSubjectType
from hei_fastapi_ddd.shared.config.enums import AccountType


class IamRelationRepositoryPort(Protocol):
    """账户/角色/组等资源授权关系。"""

    async def list_subject_resource_grants(
        self,
        subject_type: GrantSubjectType,
        subject_id: str,
        account_type: AccountType | str | None = None,
    ) -> list[dict[str, Any]]:
        ...

    async def replace_subject_resource_grant_infos(
        self,
        subject_type: GrantSubjectType,
        subject_id: str,
        grant_info_list: Any,
        account_type: AccountType | str,
    ) -> None:
        ...

    async def list_subject_client_resource_grants(
        self,
        subject_type: GrantSubjectType,
        subject_id: str,
        account_type: AccountType | str | None = None,
    ) -> list[dict[str, Any]]:
        ...

    async def replace_subject_client_resource_grant_infos(
        self,
        subject_type: GrantSubjectType,
        subject_id: str,
        grant_info_list: Any,
        account_type: AccountType | str,
    ) -> None:
        ...

    async def get_account_authorization(self, account_id: str) -> dict[str, Any]:
        ...

    async def get_accounts_authorization(
        self, account_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        ...

    async def get_account_resource_ids(self, account_id: str) -> list[str]:
        ...
