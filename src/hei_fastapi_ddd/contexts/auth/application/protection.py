""" Author: Charlie

登录保护：基于 Redis 统计账户与 IP 的失败次数并触发限流锁定。
"""

from hei_fastapi_ddd.contexts.auth.domain.policy import get_login_policy
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.exceptions.business import AuthenticationError
from hei_fastapi_ddd.shared.observability.metrics import record_login_lock
from hei_fastapi_ddd.shared.redis.keys import (
    login_failure_account_key,
    login_failure_ip_key,
    login_lock_account_key,
    login_lock_ip_key,
)
from hei_fastapi_ddd.shared.redis.redis import get_redis


class LoginProtectionService:
    """基于 Redis 的登录限流，按账户与客户端 IP 统计。"""

    async def ensure_allowed(
        self,
        *,
        account_type: AccountType,
        account: str,
        client_ip: str | None,
    ) -> None:
        """检查账户与 IP 是否处于锁定状态，锁定则抛认证错误。"""
        redis = get_redis()
        if redis is None:
            return
        normalized_account = self._normalize_account(account)
        if await redis.get(login_lock_account_key(account_type.value, normalized_account)):
            raise AuthenticationError("Account is temporarily locked")
        if client_ip and await redis.get(login_lock_ip_key(account_type.value, client_ip)):
            raise AuthenticationError("Too many failed login attempts from this IP")

    async def record_failure(
        self,
        *,
        account_type: AccountType,
        account: str,
        client_ip: str | None,
    ) -> None:
        """记录一次失败登录，累计达到阈值后锁定账户与 IP。"""
        redis = get_redis()
        if redis is None:
            return
        policy = get_login_policy(account_type)
        normalized_account = self._normalize_account(account)
        await self._increase_failure(
            redis,
            key=login_failure_account_key(account_type.value, normalized_account),
            lock_key=login_lock_account_key(account_type.value, normalized_account),
            max_failures=policy.max_failures,
            window_seconds=policy.failure_window_seconds,
            lock_seconds=policy.lock_seconds,
            account_type=account_type.value,
            scope="account",
        )
        if client_ip:
            await self._increase_failure(
                redis,
                key=login_failure_ip_key(account_type.value, client_ip),
                lock_key=login_lock_ip_key(account_type.value, client_ip),
                max_failures=settings.auth.login_ip_max_failures,
                window_seconds=settings.auth.login_failure_window_seconds,
                lock_seconds=settings.auth.login_lock_seconds,
                account_type=account_type.value,
                scope="ip",
            )

    async def record_success(
        self,
        *,
        account_type: AccountType,
        account: str,
        client_ip: str | None,
    ) -> None:
        """登录成功后清空对应账户/IP 的失败计数。"""
        redis = get_redis()
        if redis is None:
            return
        normalized_account = self._normalize_account(account)
        keys = [login_failure_account_key(account_type.value, normalized_account)]
        if client_ip:
            keys.append(login_failure_ip_key(account_type.value, client_ip))
        try:
            await redis.delete(*keys)
        except TypeError:
            for key in keys:
                await redis.delete(key)

    async def _increase_failure(
        self,
        redis,
        *,
        key: str,
        lock_key: str,
        max_failures: int,
        window_seconds: int,
        lock_seconds: int,
        account_type: str,
        scope: str,
    ) -> None:
        """递增失败计数并在达到阈值时写入锁并记录指标。"""
        count = await self._increment_failure_counter(redis, key, window_seconds)
        if count >= max_failures:
            await redis.setex(lock_key, lock_seconds, "1")
            await redis.delete(key)
            record_login_lock(account_type, scope)

    async def _increment_failure_counter(self, redis, key: str, window_seconds: int) -> int:
        """递增失败计数器；兼容带 incr 与普通 get/set 的 Redis 客户端。"""
        if hasattr(redis, "incr"):
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window_seconds)
            return int(count)
        raw = await redis.get(key)
        count = int(raw or 0) + 1
        await redis.setex(key, window_seconds, str(count))
        return count

    def _normalize_account(self, account: str) -> str:
        """规范化账户标识：去空白并转小写。"""
        return account.strip().lower()


# 模块级单例，供认证服务共享登录限流状态。
login_protection_service = LoginProtectionService()
