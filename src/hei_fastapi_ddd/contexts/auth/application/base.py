""" Author: Charlie

认证服务：登录签发、登录验证码、注册、密码找回/重置、注销与账号注销等核心业务逻辑。
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.auth.application.session_service import AccountSessionService
from hei_fastapi_ddd.contexts.iam.application.api.account_api_adapter import (
    AccountApiAdapter as AccountRepository,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import (
    IamRelationRepository,
)
from hei_fastapi_ddd.shared.audit.context import get_after, get_before, get_resource_id, get_subject
from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.exceptions.business import AuthenticationError, BusinessError
from hei_fastapi_ddd.shared.redis.redis import get_redis
from hei_fastapi_ddd.shared.security.password import verify_password_async
from hei_fastapi_ddd.shared.security.session import SessionPayload

# 各账户类型对应的密码重置链接模板配置键。
_PASSWORD_RESET_URL_KEYS = {
    AccountType.ADMIN: "AUTH_PASSWORD_RESET_URL_ADMIN",
    AccountType.PORTAL: "AUTH_PASSWORD_RESET_URL_PORTAL",
}


def session_expires_in(session: SessionPayload) -> int | None:
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


class AuthServiceBase:
    """认证服务共享依赖与账户校验。"""

    def __init__(self, db: AsyncSession):
        """初始化仓储与账户会话服务。"""
        self.db = db
        self.account_repo = AccountRepository(db)
        self.session_service = AccountSessionService(db)
        self.relation_repo = IamRelationRepository(db)

    async def _validate_account(
        self,
        account: SysAccount | None,
        password: str,
        account_type: AccountType,
    ) -> None:
        """校验账号密码、账号状态以及目标账户类型是否允许访问。"""
        if not account or not await verify_password_async(password, account.password_hash):
            raise AuthenticationError("Invalid account or password")
        self._validate_account_status(account, account_type)

    def _validate_account_status(
        self,
        account: SysAccount | None,
        account_type: AccountType,
    ) -> None:
        """校验账号状态、注销标记与目标账户类型是否允许访问。"""
        if account is None:
            raise AuthenticationError("Invalid account or password")
        if (
            account.account_status == AccountStatusEnum.CANCELLED.value
            or account.cancelled_at is not None
        ):
            raise AuthenticationError("Account is cancelled")
        if account.account_status != AccountStatusEnum.ENABLED.value:
            raise AuthenticationError("Account is inactive")
        if account_type == AccountType.ADMIN and account.account_type != AccountType.ADMIN.value:
            raise AuthenticationError("Account is not allowed to access admin account type")
        if account_type == AccountType.PORTAL and account.account_type != AccountType.PORTAL.value:
            raise AuthenticationError("Account is not allowed to access portal account type")

    def _required_redis(self, message: str = "Redis is required"):
        """获取 Redis 客户端，未初始化时抛出统一业务错误。"""
        redis = get_redis()
        if redis is None:
            raise BusinessError(message)
        return redis
