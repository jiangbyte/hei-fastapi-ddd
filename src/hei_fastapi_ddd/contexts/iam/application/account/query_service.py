""" Author: Charlie

账户读侧组装服务：将账户主表、登录标识与用户中心资料组装为统一响应 Schema。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.schema.datetime import normalize_orm_datetimes
from hei_fastapi_ddd.contexts.auth.infrastructure.persistence.oauth_repository import AccountOauthBindingRepository
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import AccountRepository
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityBindStatus
from hei_fastapi_ddd.contexts.iam.interfaces.http.iam_schemas import (
    AccountIdentitySchema,
    AccountOauthBindingSchema,
    SysAccountListSchema,
    SysAccountSchema,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.admin_repository import ProfileUserAdminRepository
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence.portal_repository import ProfileUserPortalRepository
from hei_fastapi_ddd.contexts.sys.application.file.file_application_service import FileService


class AccountQueryService:
    """IAM 与用户中心模块共用的账户读侧组装逻辑。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AccountRepository(db)

    async def build_account_schemas(self, accounts: list) -> list[SysAccountSchema]:
        """将账户 ORM 列表批量组装为 SysAccountSchema，避免逐条 N+1 查询。"""
        account_ids = [account.id for account in accounts]
        identities = await self.repo.list_identities_by_account_ids(account_ids)
        admin_profiles = await ProfileUserAdminRepository(self.db).list_by_account_ids(account_ids)
        portal_profiles = await ProfileUserPortalRepository(self.db).list_by_account_ids(
            account_ids
        )
        bindings = await AccountOauthBindingRepository(self.db).list_by_account_ids(account_ids)
        identity_map: dict[str, list] = {}
        for identity in identities:
            identity_map.setdefault(identity.account_id, []).append(identity)
        binding_map: dict[str, list] = {}
        for binding in bindings:
            binding_map.setdefault(binding.account_id, []).append(binding)
        admin_profile_map = {profile.account_id: profile for profile in admin_profiles}
        portal_profile_map = {profile.account_id: profile for profile in portal_profiles}

        avatar_raws = [
            getattr(
                (
                    admin_profile_map.get(account.id)
                    if account.account_type == AccountType.ADMIN.value
                    else portal_profile_map.get(account.id)
                    if account.account_type == AccountType.PORTAL.value
                    else None
                ),
                "avatar",
                None,
            )
            for account in accounts
        ]
        avatar_urls = await FileService(self.db).resolve_access_urls(avatar_raws)

        items: list[SysAccountSchema] = []
        for account in accounts:
            account_identities = identity_map.get(account.id, [])
            # 优先取主账号标识，回退到任意账号标识，保证 account 字段非空。
            primary_identity = next(
                (
                    item
                    for item in account_identities
                    if item.identity_type == "ACCOUNT" and item.is_primary
                ),
                None,
            ) or next(
                (item for item in account_identities if item.identity_type == "ACCOUNT"),
                None,
            )
            email_identity = next(
                (item for item in account_identities if item.identity_type == "EMAIL"),
                None,
            )
            phone_identity = next(
                (item for item in account_identities if item.identity_type == "PHONE"),
                None,
            )
            match account.account_type:
                case AccountType.ADMIN.value:
                    profile = admin_profile_map.get(account.id)
                case AccountType.PORTAL.value:
                    profile = portal_profile_map.get(account.id)
                case _:
                    profile = None
            normalize_orm_datetimes(account)
            if profile is not None:
                normalize_orm_datetimes(profile)
            for identity in account_identities:
                normalize_orm_datetimes(identity)
            raw_avatar = getattr(profile, "avatar", None)
            resolved_avatar = (
                avatar_urls.get(str(raw_avatar).strip()) if raw_avatar else None
            )
            items.append(
                SysAccountSchema(
                    id=account.id,
                    account=getattr(primary_identity, "identifier", ""),
                    account_type=account.account_type,
                    account_status=account.account_status,
                    name=None,
                    nickname=getattr(profile, "nickname", None),
                    avatar=resolved_avatar,
                    signature=getattr(profile, "signature", None),
                    phone=getattr(profile, "phone", None),
                    email=getattr(profile, "email", None),
                    email_login_enabled=_identity_login_enabled(email_identity),
                    phone_login_enabled=_identity_login_enabled(phone_identity),
                    bio=getattr(profile, "bio", None),
                    level=getattr(profile, "level", None),
                    remark=getattr(profile, "remark", None),
                    email_identity=getattr(email_identity, "identifier", None),
                    phone_identity=getattr(phone_identity, "identifier", None),
                    email_identity_verified=bool(getattr(email_identity, "verified", False)),
                    phone_identity_verified=bool(getattr(phone_identity, "verified", False)),
                    email_identity_bind_status=getattr(email_identity, "bind_status", None),
                    phone_identity_bind_status=getattr(phone_identity, "bind_status", None),
                    identities=[
                        AccountIdentitySchema.model_validate(identity)
                        for identity in account_identities
                    ],
                    oauth_bindings=[
                        AccountOauthBindingSchema.model_validate(binding)
                        for binding in binding_map.get(account.id, [])
                    ],
                    cancelled_at=account.cancelled_at,
                    cancelled_by=account.cancelled_by,
                    cancel_reason=account.cancel_reason,
                    last_login_ip=account.last_login_ip,
                    last_login_address=account.last_login_address,
                    last_login_time=account.last_login_time,
                    last_login_device=account.last_login_device,
                    latest_login_ip=account.latest_login_ip,
                    latest_login_address=account.latest_login_address,
                    latest_login_time=account.latest_login_time,
                    latest_login_device=account.latest_login_device,
                    created_at=account.created_at,
                    created_by=account.created_by,
                    updated_at=account.updated_at,
                    updated_by=account.updated_by,
                )
            )
        return items

    async def build_account_list_schemas(self, accounts: list) -> list[SysAccountListSchema]:
        """分页列表：仅组装 account 主表与 profile 展示字段。"""
        account_ids = [account.id for account in accounts]
        identities = await self.repo.list_identities_by_account_ids(account_ids)
        admin_profiles = await ProfileUserAdminRepository(self.db).list_by_account_ids(account_ids)
        portal_profiles = await ProfileUserPortalRepository(self.db).list_by_account_ids(
            account_ids
        )
        identity_map: dict[str, list] = {}
        for identity in identities:
            identity_map.setdefault(identity.account_id, []).append(identity)
        admin_profile_map = {profile.account_id: profile for profile in admin_profiles}
        portal_profile_map = {profile.account_id: profile for profile in portal_profiles}

        avatar_raws = []
        for account in accounts:
            match account.account_type:
                case AccountType.ADMIN.value:
                    profile = admin_profile_map.get(account.id)
                case AccountType.PORTAL.value:
                    profile = portal_profile_map.get(account.id)
                case _:
                    profile = None
            avatar_raws.append(getattr(profile, "avatar", None))
        avatar_urls = await FileService(self.db).resolve_access_urls(avatar_raws)

        items: list[SysAccountListSchema] = []
        for account, raw_avatar in zip(accounts, avatar_raws, strict=True):
            account_identities = identity_map.get(account.id, [])
            primary_identity = next(
                (
                    item
                    for item in account_identities
                    if item.identity_type == "ACCOUNT" and item.is_primary
                ),
                None,
            ) or next(
                (item for item in account_identities if item.identity_type == "ACCOUNT"),
                None,
            )
            match account.account_type:
                case AccountType.ADMIN.value:
                    profile = admin_profile_map.get(account.id)
                case AccountType.PORTAL.value:
                    profile = portal_profile_map.get(account.id)
                case _:
                    profile = None
            normalize_orm_datetimes(account)
            resolved_avatar = (
                avatar_urls.get(str(raw_avatar).strip()) if raw_avatar else None
            )
            items.append(
                SysAccountListSchema(
                    id=account.id,
                    account=getattr(primary_identity, "identifier", ""),
                    account_type=account.account_type,
                    account_status=account.account_status,
                    nickname=getattr(profile, "nickname", None),
                    avatar=resolved_avatar,
                    phone=getattr(profile, "phone", None),
                    email=getattr(profile, "email", None),
                    remark=getattr(profile, "remark", None),
                    latest_login_time=account.latest_login_time,
                    updated_at=account.updated_at,
                )
            )
        return items

    async def build_account_picker_schemas(self, accounts: list) -> list[SysAccountSchema]:
        """授权弹窗候选用户：仅批量组装 id/账号/昵称/头像等展示字段，跳过 OAuth 与完整 identity 列表。"""
        account_ids = [account.id for account in accounts]
        identities = await self.repo.list_identities_by_account_ids(account_ids)
        admin_profiles = await ProfileUserAdminRepository(self.db).list_by_account_ids(account_ids)
        portal_profiles = await ProfileUserPortalRepository(self.db).list_by_account_ids(
            account_ids
        )
        identity_map: dict[str, list] = {}
        for identity in identities:
            identity_map.setdefault(identity.account_id, []).append(identity)
        admin_profile_map = {profile.account_id: profile for profile in admin_profiles}
        portal_profile_map = {profile.account_id: profile for profile in portal_profiles}

        avatar_raws = []
        for account in accounts:
            match account.account_type:
                case AccountType.ADMIN.value:
                    profile = admin_profile_map.get(account.id)
                case AccountType.PORTAL.value:
                    profile = portal_profile_map.get(account.id)
                case _:
                    profile = None
            avatar_raws.append(getattr(profile, "avatar", None))
        avatar_urls = await FileService(self.db).resolve_access_urls(avatar_raws)

        items: list[SysAccountSchema] = []
        for account, raw_avatar in zip(accounts, avatar_raws, strict=True):
            account_identities = identity_map.get(account.id, [])
            primary_identity = next(
                (
                    item
                    for item in account_identities
                    if item.identity_type == "ACCOUNT" and item.is_primary
                ),
                None,
            ) or next(
                (item for item in account_identities if item.identity_type == "ACCOUNT"),
                None,
            )
            match account.account_type:
                case AccountType.ADMIN.value:
                    profile = admin_profile_map.get(account.id)
                case AccountType.PORTAL.value:
                    profile = portal_profile_map.get(account.id)
                case _:
                    profile = None
            normalize_orm_datetimes(account)
            resolved_avatar = (
                avatar_urls.get(str(raw_avatar).strip()) if raw_avatar else None
            )
            items.append(
                SysAccountSchema(
                    id=account.id,
                    account=getattr(primary_identity, "identifier", ""),
                    account_type=account.account_type,
                    account_status=account.account_status,
                    name=None,
                    nickname=getattr(profile, "nickname", None),
                    avatar=resolved_avatar,
                    created_at=account.created_at,
                    updated_at=account.updated_at,
                )
            )
        return items


def _identity_login_enabled(identity) -> bool:
    """判断登录标识是否已启用：存在、已验证且处于绑定状态（对齐 hei-boot）。"""
    return bool(
        identity
        and identity.identifier
        and identity.verified
        and identity.bind_status == AccountIdentityBindStatus.BOUND.value
    )
