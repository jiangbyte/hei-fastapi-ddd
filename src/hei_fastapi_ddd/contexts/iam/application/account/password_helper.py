"""Author: Charlie

密码管理辅助：强度校验、历史复用检查与过期检测（不依赖 infrastructure）。
"""

from __future__ import annotations

from datetime import UTC, datetime

from hei_fastapi_ddd.contexts.iam.domain.account.password_port import AccountPasswordPort
from hei_fastapi_ddd.contexts.iam.domain.account.repository import AccountRepository
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.security.password import hash_password_async
from hei_fastapi_ddd.shared.security.password_policy import (
    is_weak_password,
    validate_password_strength,
)
from hei_fastapi_ddd.types.business import BusinessError


def _parse_dt(value) -> datetime | None:
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
    db,
    account_id: str,
    plain_password: str,
    *,
    changed_by: str | None = None,
    change_reason: str | None = None,
    account_repo: AccountRepository,
    password_port: AccountPasswordPort,
    account_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> None:
    """校验密码强度、检查历史复用并记录。"""
    # 1. 强度与弱密码库
    validate_password_strength(plain_password)
    policy = settings.password_policy
    if policy.common_password_check and await is_weak_password(db, plain_password):
        raise BusinessError("密码过于常见，请更换")

    # 2. 用户信息禁含
    if policy.forbid_user_info:
        resolved_email = email
        resolved_phone = phone
        resolved_name = account_name
        if resolved_email is None or resolved_phone is None or resolved_name is None:
            identities = await account_repo.list_identities_by_account_ids([account_id])
            for item in identities:
                identity_type = item.get("identity_type")
                identifier = item.get("identifier")
                if identity_type == "ACCOUNT" and not resolved_name:
                    resolved_name = identifier
                elif identity_type == "EMAIL" and not resolved_email:
                    resolved_email = identifier
                elif identity_type == "PHONE" and not resolved_phone:
                    resolved_phone = identifier
        if _contains_user_info(
            plain_password,
            account_name=resolved_name,
            email=resolved_email,
            phone=resolved_phone,
        ):
            raise BusinessError("密码不能包含账号、邮箱或手机号等用户信息")

    # 3. 历史复用
    if policy.forbid_historical:
        count = settings.password_policy.history_check_count
        if count > 0 and await password_port.matches_any_history(
            account_id, plain_password, count
        ):
            raise BusinessError(f"新密码不能与最近 {count} 次使用过的密码相同")

    # 4. 写入历史
    await password_port.append(
        account_id,
        plain_password,
        changed_by=changed_by,
        change_reason=change_reason,
    )


async def get_password_age_days(
    password_port: AccountPasswordPort,
    account_id: str,
) -> float | None:
    row = await password_port.get_latest_changed_at(account_id)
    if row is None:
        return None
    dt = _parse_dt(row)
    if dt is None:
        return None
    return (datetime.now(UTC) - dt).total_seconds() / 86400


async def is_password_expired(password_port: AccountPasswordPort, account_id: str) -> bool:
    expire_days = settings.password_policy.expire_days
    if expire_days <= 0:
        return False
    age_days = await get_password_age_days(password_port, account_id)
    if age_days is None:
        return False
    return age_days >= expire_days
