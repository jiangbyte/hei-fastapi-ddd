""" Author: Charlie

账户会话服务：从授权信息构建/刷新会话载荷，并代理会话存储的删除操作。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.application.api.account_api import AccountApi
from hei_fastapi_ddd.contexts.iam.domain.relation.repository import IamRelationRepositoryPort
from hei_fastapi_ddd.contexts.iam.domain.role.constants import SUPER_ADMIN_ROLE_CODE
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store


class AccountSessionService:
    """构建并刷新账户会话，不依赖 auth 业务流程。"""

    def __init__(
        self,
        db: AsyncSession,
        *,
        account_api: AccountApi,
        relation_repo: IamRelationRepositoryPort,
    ):
        """初始化账户与关系端口。"""
        self.db = db
        self.account_api = account_api
        self.relation_repo = relation_repo

    async def build_session_payload(
        self,
        account: Mapping[str, Any],
        token: str,
        *,
        remember_me: bool = True,
        password_expired: bool = False,
        client_ip: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
    ) -> SessionPayload:
        """根据账户授权构建会话载荷。"""
        authorization = await self.relation_repo.get_account_authorization(str(account["id"]))
        return self._build_session_payload_from_authorization(
            account,
            token,
            authorization,
            remember_me=remember_me,
            password_expired=password_expired,
            client_ip=client_ip,
            user_agent=user_agent,
            device_label=device_label,
        )

    async def refresh_account_sessions(self, account_id: str) -> None:
        """刷新单个账户的在线会话。"""
        await self.refresh_accounts_sessions([account_id])

    async def refresh_accounts_sessions(self, account_ids: list[str]) -> None:
        """批量刷新账户的在线会话（重新计算授权）。"""
        accounts = await self.account_api.list_accounts_by_ids(account_ids)
        if not accounts:
            return
        authorizations = await self.relation_repo.get_accounts_authorization(
            [str(item["id"]) for item in accounts]
        )
        targets = [(str(account["account_type"]), str(account["id"])) for account in accounts]
        payload_factories = {}

        for account in accounts:
            account_id = str(account["id"])
            authorization = authorizations[account_id]

            async def payload_factory(
                token: str,
                old: SessionPayload,
                current_account: Mapping[str, Any] = account,
                current_authorization: dict = authorization,
            ) -> SessionPayload:
                return self._build_session_payload_from_authorization(
                    current_account,
                    token,
                    current_authorization,
                    remember_me=old.remember_me,
                )

            payload_factories[(str(account["account_type"]), account_id)] = payload_factory

        await session_store.refresh_accounts_sessions(targets, payload_factories)

    async def delete_account_sessions(self, account_type: str, account_id: str) -> None:
        """删除单个账户的在线会话。"""
        await session_store.delete_account_sessions(account_type, account_id)

    async def delete_accounts_sessions(self, targets: list[tuple[str, str]]) -> None:
        """批量删除账户的在线会话。"""
        await session_store.delete_accounts_sessions(targets)

    def _build_session_payload_from_authorization(
        self,
        account: Mapping[str, Any],
        token: str,
        authorization: dict,
        *,
        remember_me: bool = True,
        password_expired: bool = False,
        client_ip: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
    ) -> SessionPayload:
        """从授权信息组装会话载荷，含超管权限注入。"""
        permission_keys = set(authorization["permission_keys"])
        if SUPER_ADMIN_ROLE_CODE in authorization["role_codes"]:
            permission_keys.add("*:*:*")
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=settings.auth.token_ttl_seconds)
        return SessionPayload(
            token=token,
            account_id=str(account["id"]),
            account_type=str(account["account_type"]),
            remember_me=remember_me,
            password_expired=password_expired,
            role_ids=authorization["role_ids"],
            dept_ids=authorization["dept_ids"],
            group_ids=authorization["group_ids"],
            resource_ids=[],
            permission_keys=sorted(permission_keys),
            permission_grants=authorization["permission_grants"],
            client_resource_ids=list(authorization.get("client_resource_ids") or []),
            client_permission_keys=list(authorization.get("client_permission_keys") or []),
            client_ip=client_ip,
            user_agent=user_agent,
            device_label=device_label,
            login_at=now.isoformat(),
            last_active_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
        )
