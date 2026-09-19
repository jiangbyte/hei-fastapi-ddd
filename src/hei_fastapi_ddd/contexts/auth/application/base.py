""" Author: Charlie

认证服务：登录签发、登录验证码、注册、密码找回/重置、注销与账号注销等核心业务逻辑。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.auth.application.session_service import AccountSessionService
from hei_fastapi_ddd.contexts.iam.application.api.account_api import AccountApi
from hei_fastapi_ddd.contexts.iam.domain.account.password_port import AccountPasswordPort
from hei_fastapi_ddd.contexts.iam.domain.relation.repository import IamRelationRepositoryPort
from hei_fastapi_ddd.contexts.profile.application.api.profile_read_port import ProfileReadPort
from hei_fastapi_ddd.contexts.profile.application.api.profile_upsert_port import ProfileUpsertPort
from hei_fastapi_ddd.shared.audit.context import get_after, get_before, get_resource_id, get_subject
from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.types.business import AuthenticationError, BusinessError

# 各账户类型对应的密码重置链接模板配置键。
_PASSWORD_RESET_URL_KEYS = {
    AccountType.ADMIN: "AUTH_PASSWORD_RESET_URL_ADMIN",
    AccountType.PORTAL: "AUTH_PASSWORD_RESET_URL_PORTAL",
}


def session_expires_in(session) -> int | None:
    """返回会话剩余有效秒数（按 expires_at 计算），无法计算时返回 None。"""
    if not session.expires_at:
        return None
    try:
        expires_at = datetime.fromisoformat(session.expires_at)
    except (TypeError, ValueError):
        return None
    remaining = int((expires_at - datetime.now(UTC)).total_seconds())
    return remaining if remaining > 0 else None


def _audit_record_context() -> dict[str, Any]:
    """读取 AuditSnapshots 上下文为 record() 关键字参数字典。"""
    kwargs: dict[str, Any] = {}
    if subject := get_subject():
        kwargs["subject"] = subject
    if resource_id := get_resource_id():
        kwargs["resource_id"] = resource_id
    before = get_before()
    after = get_after()
    if before:
        kwargs["before_data"] = before
    if after:
        kwargs["after_data"] = after
    return kwargs


def _audit_record(**kwargs: Any) -> dict[str, Any]:
    """合并快照上下文与显式参数；显式参数覆盖同名字段。"""
    return {**_audit_record_context(), **kwargs}


def _account_id(account: Mapping[str, Any]) -> str:
    return str(account["id"])


class AuthServiceBase:
    """认证服务共享依赖与账户校验。"""

    def __init__(
        self,
        db: AsyncSession,
        *,
        account_api: AccountApi,
        relation_repo: IamRelationRepositoryPort,
        session_service: AccountSessionService,
        profile_port: ProfileUpsertPort,
        password_port: AccountPasswordPort,
        profile_read_port: ProfileReadPort,
    ):
        """注入跨 BC 端口与本 BC 会话服务。"""
        self.db = db
        self.account_api = account_api
        self.account_repo = account_api
        self.relation_repo = relation_repo
        self.session_service = session_service
        self.profile_port = profile_port
        self.password_port = password_port
        self.profile_read_port = profile_read_port

    async def _validate_account(
        self,
        account: Mapping[str, Any] | None,
        password: str,
        account_type: AccountType,
    ) -> None:
        """校验账号密码、账号状态以及目标账户类型是否允许访问。"""
        if account is None or not await self.account_api.verify_password(account, password):
            raise AuthenticationError("Invalid account or password")
        self._validate_account_status(account, account_type)

    def _validate_account_status(
        self,
        account: Mapping[str, Any] | None,
        account_type: AccountType,
    ) -> None:
        """校验账号状态、注销标记与目标账户类型是否允许访问。"""
        if account is None:
            raise AuthenticationError("Invalid account or password")
        if (
            account.get("account_status") == AccountStatusEnum.CANCELLED.value
            or account.get("cancelled_at") is not None
        ):
            raise AuthenticationError("Account is cancelled")
        if account.get("account_status") != AccountStatusEnum.ENABLED.value:
            raise AuthenticationError("Account is inactive")
        if account_type == AccountType.ADMIN and account.get("account_type") != AccountType.ADMIN.value:
            raise AuthenticationError("Account is not allowed to access admin account type")
        if account_type == AccountType.PORTAL and account.get("account_type") != AccountType.PORTAL.value:
            raise AuthenticationError("Account is not allowed to access portal account type")

    def _required_redis(self, message: str = "Redis is required"):
        """获取 Redis 客户端，未初始化时抛出统一业务错误。"""
        redis = get_redis()
        if redis is None:
            raise BusinessError(message)
        return redis

    async def _assign_register_defaults(self, account_id: str, account_type: AccountType) -> None:
        """为注册账户分配策略中配置的默认角色与部门。"""
        from hei_fastapi_ddd.contexts.auth.domain.policy import get_register_policy

        policy = get_register_policy(account_type)
        if policy.default_role_id:
            await self.account_api.assign_account_to_role(
                {"account_id": account_id, "role_id": policy.default_role_id}
            )
        if policy.default_dept_id:
            await self.account_api.assign_account_to_dept(
                {
                    "account_id": account_id,
                    "dept_id": policy.default_dept_id,
                    "is_primary": True,
                }
            )
