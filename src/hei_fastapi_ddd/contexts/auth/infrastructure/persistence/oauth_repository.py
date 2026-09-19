""" Author: Charlie

三方登录绑定仓储：按提供商/openid/unionid 查询与绑定维护。
"""

from collections.abc import Iterable

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.auth.infrastructure.persistence.oauth_po import SysAccountOauthBinding
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.types.business import BusinessError

# 微信族提供商（开放平台 + 小程序），unionid 可跨端关联。
WECHAT_FAMILY = {"WECHAT_OPEN", "WECHAT_MP"}


class AccountOauthBindingRepository:
    """账号三方绑定数据仓储。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_provider_open_id(
        self, provider: str, open_id: str
    ) -> SysAccountOauthBinding | None:
        """按提供商 + openid 查找绑定；无则返回 None。"""
        stmt = select(SysAccountOauthBinding).where(
            SysAccountOauthBinding.provider == provider,
            SysAccountOauthBinding.open_id == open_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_by_wechat_union_id(self, union_id: str) -> SysAccountOauthBinding | None:
        """按微信 unionid 查找任一微信族绑定（WECHAT_OPEN / WECHAT_MP）。"""
        if not union_id:
            return None
        stmt = (
            select(SysAccountOauthBinding)
            .where(
                SysAccountOauthBinding.union_id == union_id,
                SysAccountOauthBinding.provider.in_(sorted(WECHAT_FAMILY)),
            )
            .order_by(SysAccountOauthBinding.bound_at.asc())
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def list_by_account(self, account_id: str) -> list[SysAccountOauthBinding]:
        """列出账号全部三方绑定。"""
        stmt = (
            select(SysAccountOauthBinding)
            .where(SysAccountOauthBinding.account_id == account_id)
            .order_by(SysAccountOauthBinding.bound_at.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_by_account_ids(
        self, account_ids: Iterable[str]
    ) -> list[SysAccountOauthBinding]:
        """按账号 ID 批量列出三方绑定。"""
        unique = list(dict.fromkeys(account_ids))
        if not unique:
            return []
        stmt = select(SysAccountOauthBinding).where(
            SysAccountOauthBinding.account_id.in_(unique)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def count_by_account(self, account_id: str) -> int:
        """统计账号绑定数量。"""
        stmt = select(func.count(SysAccountOauthBinding.id)).where(
            SysAccountOauthBinding.account_id == account_id
        )
        return int((await self.db.execute(stmt)).scalar_one())

    async def upsert_binding(
        self,
        account_id: str,
        provider: str,
        open_id: str,
        union_id: str | None = None,
        nickname: str | None = None,
        avatar: str | None = None,
        raw_profile_json: str | dict | None = None,
    ) -> SysAccountOauthBinding:
        """新增或更新绑定：同账号同 provider 唯一，provider+openid 全局唯一。

        若该 openid 已被其他账号绑定则拒绝，避免串号。
        """
        existing = await self.find_by_provider_open_id(provider, open_id)
        if existing is not None and existing.account_id != account_id:
            raise BusinessError("该三方账号已绑定其他用户")
        same_account = (
            await self.db.execute(
                select(SysAccountOauthBinding).where(
                    SysAccountOauthBinding.account_id == account_id,
                    SysAccountOauthBinding.provider == provider,
                )
            )
        ).scalar_one_or_none()
        raw = (
            raw_profile_json
            if isinstance(raw_profile_json, dict)
            else {"raw": raw_profile_json}
            if raw_profile_json
            else {}
        )
        if same_account is None:
            entity = SysAccountOauthBinding(
                id=generate_snowflake_id(),
                account_id=account_id,
                provider=provider,
                open_id=open_id,
                union_id=union_id,
                nickname=nickname,
                avatar=avatar,
                raw_profile=raw,
            )
            self.db.add(entity)
            await self.db.flush()
            return entity
        same_account.open_id = open_id
        if union_id is not None:
            same_account.union_id = union_id
        if nickname is not None:
            same_account.nickname = nickname
        if avatar is not None:
            same_account.avatar = avatar
        if raw:
            same_account.raw_profile = raw
        await self.db.flush()
        return same_account

    async def unbind(self, account_id: str, provider: str) -> None:
        """解绑指定提供商；不存在时静默成功。"""
        await self.db.execute(
            delete(SysAccountOauthBinding).where(
                SysAccountOauthBinding.account_id == account_id,
                SysAccountOauthBinding.provider == provider,
            )
        )
        await self.db.flush()
