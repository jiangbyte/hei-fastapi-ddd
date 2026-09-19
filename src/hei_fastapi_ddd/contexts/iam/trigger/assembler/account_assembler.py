"""Author: Charlie

账户 HTTP 组装：dict 视图 → api Schema（仅 trigger 依赖 api）。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.auth.infrastructure.persistence.oauth_repository import (
    AccountOauthBindingRepository,
)
from hei_fastapi_ddd.contexts.iam.api.iam_schemas import (
    AccountIdentitySchema,
    AccountOauthBindingSchema,
    SysAccountListSchema,
    SysAccountSchema,
)
from hei_fastapi_ddd.contexts.iam.application.account.account_read_service import AccountReadService
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import (
    AccountRepositoryImpl,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.api.profile_read_adapter import (
    ProfileReadAdapter,
)
from hei_fastapi_ddd.contexts.sys.application.file.file_application_service import FileService
from hei_fastapi_ddd.shared.schema.datetime import normalize_orm_datetimes


class AccountAssembler:
    """账户响应 Schema 组装。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._read = AccountReadService(AccountRepositoryImpl(db), ProfileReadAdapter(db))

    async def build_account_schemas(self, accounts: list[dict]) -> list[SysAccountSchema]:
        views = await self._read.build_account_views(accounts, full=True)
        account_ids = [str(a["id"]) for a in accounts]
        bindings = await AccountOauthBindingRepository(self.db).list_by_account_ids(account_ids)
        binding_map: dict[str, list] = {}
        for binding in bindings:
            binding_map.setdefault(binding.account_id, []).append(binding)
        avatar_urls = await FileService(self.db).resolve_access_urls(
            [view.get("avatar") for view in views]
        )
        items: list[SysAccountSchema] = []
        for view in views:
            raw_avatar = view.get("avatar")
            resolved = avatar_urls.get(str(raw_avatar).strip()) if raw_avatar else None
            for identity in view.get("identities") or []:
                normalize_orm_datetimes(identity)
            items.append(
                SysAccountSchema(
                    id=view["id"],
                    account=view.get("account") or "",
                    account_type=view["account_type"],
                    account_status=view["account_status"],
                    name=None,
                    nickname=view.get("nickname"),
                    avatar=resolved,
                    signature=view.get("signature"),
                    phone=view.get("phone"),
                    email=view.get("email"),
                    email_login_enabled=view.get("email_login_enabled", False),
                    phone_login_enabled=view.get("phone_login_enabled", False),
                    bio=view.get("bio"),
                    level=view.get("level"),
                    remark=view.get("remark"),
                    email_identity=view.get("email_identity"),
                    phone_identity=view.get("phone_identity"),
                    email_identity_verified=view.get("email_identity_verified", False),
                    phone_identity_verified=view.get("phone_identity_verified", False),
                    email_identity_bind_status=view.get("email_identity_bind_status"),
                    phone_identity_bind_status=view.get("phone_identity_bind_status"),
                    identities=[
                        AccountIdentitySchema.model_validate(i)
                        for i in (view.get("identities") or [])
                    ],
                    oauth_bindings=[
                        AccountOauthBindingSchema.model_validate(b)
                        for b in binding_map.get(str(view["id"]), [])
                    ],
                    cancelled_at=view.get("cancelled_at"),
                    cancelled_by=view.get("cancelled_by"),
                    cancel_reason=view.get("cancel_reason"),
                    last_login_ip=view.get("last_login_ip"),
                    last_login_address=view.get("last_login_address"),
                    last_login_time=view.get("last_login_time"),
                    last_login_device=view.get("last_login_device"),
                    latest_login_ip=view.get("latest_login_ip"),
                    latest_login_address=view.get("latest_login_address"),
                    latest_login_time=view.get("latest_login_time"),
                    latest_login_device=view.get("latest_login_device"),
                    created_at=view.get("created_at"),
                    created_by=view.get("created_by"),
                    updated_at=view.get("updated_at"),
                    updated_by=view.get("updated_by"),
                )
            )
        return items

    async def build_account_list_schemas(self, accounts: list[dict]) -> list[SysAccountListSchema]:
        views = await self._read.build_account_views(accounts, full=False)
        avatar_urls = await FileService(self.db).resolve_access_urls(
            [view.get("avatar") for view in views]
        )
        items: list[SysAccountListSchema] = []
        for view in views:
            raw_avatar = view.get("avatar")
            resolved = avatar_urls.get(str(raw_avatar).strip()) if raw_avatar else None
            items.append(
                SysAccountListSchema(
                    id=view["id"],
                    account=view.get("account") or "",
                    account_type=view["account_type"],
                    account_status=view["account_status"],
                    nickname=view.get("nickname"),
                    avatar=resolved,
                    phone=view.get("phone"),
                    email=view.get("email"),
                    remark=view.get("remark"),
                    latest_login_time=view.get("latest_login_time"),
                    updated_at=view.get("updated_at"),
                )
            )
        return items

    async def build_account_picker_schemas(self, accounts: list[dict]) -> list[SysAccountSchema]:
        views = await self._read.build_account_views(accounts, full=False)
        avatar_urls = await FileService(self.db).resolve_access_urls(
            [view.get("avatar") for view in views]
        )
        items: list[SysAccountSchema] = []
        for view in views:
            raw_avatar = view.get("avatar")
            resolved = avatar_urls.get(str(raw_avatar).strip()) if raw_avatar else None
            items.append(
                SysAccountSchema(
                    id=view["id"],
                    account=view.get("account") or "",
                    account_type=view["account_type"],
                    account_status=view["account_status"],
                    name=None,
                    nickname=view.get("nickname"),
                    avatar=resolved,
                    created_at=view.get("created_at"),
                    updated_at=view.get("updated_at"),
                )
            )
        return items
