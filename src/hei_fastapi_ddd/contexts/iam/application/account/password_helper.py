""" Author: Charlie

密码管理辅助工具 — 强度校验、历史记录、
复用检查与过期检测。

供 ``AuthService`` 与 ``AccountService`` 执行密码策略。
"""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.exceptions.business import BusinessError
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.security.password import hash_password_async, verify_password_async
from hei_fastapi_ddd.shared.security.password_policy import is_weak_password, validate_password_strength
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.password_history_po import SysAccountPasswordHistory


def _parse_dt(value) -> datetime | None:
    """安全地将 datetime 或 None 解析为 UTC 时区的 datetime。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return None


def _contains_user_info(
    password: str,
    *,
    account_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> bool:
    lowered = password.lower()
    candidates: list[str] = []
    if account_name:
        candidates.append(account_name.strip().lower())
    if email:
        local = email.strip().lower().split("@", 1)[0]
        candidates.append(email.strip().lower())
        candidates.append(local)
    if phone:
        candidates.append(phone.strip())
    for item in candidates:
        if item and len(item) >= 3 and item in lowered:
            return True
    return False


async def validate_and_record_password(
    db: AsyncSession,
    account_id: str,
    plain_password: str,
    *,
    changed_by: str | None = None,
    change_reason: str | None = None,
    account: SysAccount | None = None,
    account_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> None:
    """校验密码强度、检查历史复用并记录。

    强度或复用违规时抛出 ``BusinessError``。
    """
    validate_password_strength(plain_password)

    policy = settings.password_policy
    if policy.common_password_check and await is_weak_password(db, plain_password):
        raise BusinessError("密码过于常见，请更换")

    if policy.forbid_user_info:
        resolved_email = email
        resolved_phone = phone
        resolved_name = account_name
        if resolved_email is None or resolved_phone is None or resolved_name is None:
            from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import AccountRepository

            identities = await AccountRepository(db).list_identities_by_account_ids([account_id])
            for item in identities:
                if item.identity_type == "ACCOUNT" and not resolved_name:
                    resolved_name = item.identifier
                elif item.identity_type == "EMAIL" and not resolved_email:
                    resolved_email = item.identifier
                elif item.identity_type == "PHONE" and not resolved_phone:
                    resolved_phone = item.identifier
        if _contains_user_info(
            plain_password,
            account_name=resolved_name,
            email=resolved_email,
            phone=resolved_phone,
        ):
            raise BusinessError("密码不能包含账号、邮箱或手机号等用户信息")

    if policy.forbid_historical:
        await _check_password_reuse(db, account_id, plain_password)

    db.add(
        SysAccountPasswordHistory(
            id=generate_snowflake_id(),
            account_id=account_id,
            password_hash=await hash_password_async(plain_password),
            changed_by=changed_by or account_id,
            change_reason=change_reason or "unknown",
        )
    )


async def _check_password_reuse(db: AsyncSession, account_id: str, new_password: str) -> None:
    """检查新密码是否与最近历史记录中的任一密码相同。"""
    count = settings.password_policy.history_check_count
    if count <= 0:
        return

    stmt = (
        select(SysAccountPasswordHistory.password_hash)
        .where(SysAccountPasswordHistory.account_id == account_id)
        .order_by(SysAccountPasswordHistory.created_at.desc())
        .limit(count)
    )
    rows = (await db.execute(stmt)).scalars().all()

    for old_hash in rows:
        if await verify_password_async(new_password, old_hash):
            raise BusinessError(f"新密码不能与最近 {count} 次使用过的密码相同")


async def get_password_age_days(db: AsyncSession, account_id: str) -> float | None:
    """返回距上次改密的天数，未知时返回 ``None``。"""
    stmt = (
        select(SysAccountPasswordHistory.created_at)
        .where(SysAccountPasswordHistory.account_id == account_id)
        .order_by(SysAccountPasswordHistory.created_at.desc())
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    dt = _parse_dt(row)
    if dt is None:
        return None
    return (datetime.now(UTC) - dt).total_seconds() / 86400


async def is_password_expired(db: AsyncSession, account_id: str) -> bool:
    """检查账户密码是否已超过配置的过期期限。"""
    expire_days = settings.password_policy.expire_days
    if expire_days <= 0:
        return False
    age_days = await get_password_age_days(db, account_id)
    if age_days is None:
        return False
    return age_days >= expire_days
