""" Author: Charlie

门户账户资料服务层：资料初始化、组织信息回显与用户中心维护。
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.auth.application.password_change import verify_change_password
from hei_fastapi_ddd.contexts.auth.application.session_service import AccountSessionService
from hei_fastapi_ddd.contexts.auth.application.api.bind_code_port import AuthBindCodePort
from hei_fastapi_ddd.contexts.iam.application.account.password_helper import validate_and_record_password
from hei_fastapi_ddd.contexts.iam.application.api.account_api import AccountApi
from hei_fastapi_ddd.contexts.iam.application.api.org_read_api import IamOrgReadApi
from hei_fastapi_ddd.contexts.iam.domain.account.password_port import AccountPasswordPort
from hei_fastapi_ddd.contexts.iam.domain.enums import AccountIdentityType
from hei_fastapi_ddd.contexts.profile.application.portal.dto import (
    PortalProfileUpsertCommand,
    PortalPublicProfileResult,
    PortalPublicSpaceQueryCommand,
    PortalUserCenterAvatarUpdateResult,
    PortalUserCenterEmailUpdateCommand,
    PortalUserCenterPasswordUpdateCommand,
    PortalUserCenterPhoneUpdateCommand,
    PortalUserCenterProfileUpdateCommand,
)
from hei_fastapi_ddd.contexts.profile.domain.portal.repository import ProfileUserPortalRepository
from hei_fastapi_ddd.contexts.sys.application.file.dto import FileUploadCommand
from hei_fastapi_ddd.contexts.sys.application.file.file_application_service import FileService
from hei_fastapi_ddd.shared.audit import snapshots as audit_snapshots
from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.persistence.transaction import transactional
from hei_fastapi_ddd.shared.schema.common_schema import IdNameResponse
from hei_fastapi_ddd.shared.security.password import hash_password_async, verify_password_async
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.storage.url import is_external_url, normalize_object_name
from hei_fastapi_ddd.types.business import AuthenticationError, BusinessError

AVATAR_MAX_SIZE = 2 * 1024 * 1024  # 头像文件大小上限（2MB）
AVATAR_CONTENT_TYPES = {  # 允许的头像内容类型及其扩展名
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class ProfileUserPortalService:
    """门户账户资料服务，负责资料初始化和显式查询。"""

    def __init__(
        self,
        db: AsyncSession,
        *,
        repo: ProfileUserPortalRepository,
        account_api: AccountApi,
        org_read_api: IamOrgReadApi,
        password_port: AccountPasswordPort,
        session_service: AccountSessionService,
        bind_code_port: AuthBindCodePort,
    ):
        self.db = db
        self.repo = repo
        self.account_api = account_api
        self.org_read_api = org_read_api
        self.password_port = password_port
        self._session_service = session_service
        self._bind_code_port = bind_code_port

    async def get_profile(self, account_id: str):
        """按账户 ID 查询门户资料，不依赖 ORM relationship 自动装配。"""
        return await self.repo.get_by_account_id(account_id)

    async def get_id_name_groups(
        self,
        role_ids: list[str],
        dept_ids: list[str],
        group_ids: list[str],
    ) -> tuple[list[IdNameResponse], list[IdNameResponse], list[IdNameResponse]]:
        """按 ID 列表批量查询角色/部门/群组名称。"""
        role_rows, dept_rows, group_rows = await self.org_read_api.list_id_name_rows(
            role_ids,
            dept_ids,
            group_ids,
        )
        return (
            [IdNameResponse(**row) for row in role_rows],
            [IdNameResponse(**row) for row in dept_rows],
            [IdNameResponse(**row) for row in group_rows],
        )

    async def get_public_profile(
        self, query: PortalPublicSpaceQueryCommand
    ) -> PortalPublicProfileResult:
        """查询门户用户公开主页资料。"""
        account_id = query.account_id
        await self.account_api.get_required(account_id)
        profile = await self.repo.get_by_account_id(account_id)
        if profile is None:
            from hei_fastapi_ddd.types.business import NotFoundError

            raise NotFoundError("Profile not found")
        return PortalPublicProfileResult(
            account_id=account_id,
            nickname=profile.get("nickname"),
            avatar=await FileService(self.db).resolve_access_url(profile.get("avatar")),
            signature=profile.get("signature"),
            bio=profile.get("bio"),
        )

    async def update_current_profile(
        self,
        payload: PortalUserCenterProfileUpdateCommand,
        session: SessionPayload,
    ) -> None:
        """更新当前账户个人资料（头像按载荷规范化写入，其余字段保留，对齐 hei-boot）。"""
        profile = await self.repo.get_by_account_id(session.account_id)
        avatar = (
            normalize_object_name(payload.avatar)
            if payload.avatar
            else (profile.get("avatar") if profile else None)
        )
        if profile is not None:
            audit_snapshots.before_entity(profile)
        async with transactional(self.db):
            await self.repo.upsert(
                PortalProfileUpsertCommand(
                    account_id=session.account_id,
                    nickname=payload.nickname,
                    avatar=avatar,
                    signature=payload.signature,
                    phone=profile.get("phone") if profile else None,
                    email=profile.get("email") if profile else None
                ).model_dump()
            )
        updated = await self.repo.get_by_account_id(session.account_id)
        if updated is not None:
            audit_snapshots.after_entity(updated)

    async def update_current_avatar(
        self,
        content: bytes,
        content_type: str,
        session: SessionPayload,
    ) -> PortalUserCenterAvatarUpdateResult:
        """上传新头像并更新资料，随后清理旧头像文件。"""
        content_type = self._normalize_avatar_content_type(content_type)
        self._ensure_avatar_file(content, content_type)
        profile = await self.repo.get_by_account_id(session.account_id)
        previous_avatar = profile.get("avatar") if profile else None
        avatar_object_name = self._build_avatar_object_name(content_type)
        uploaded_row = await FileService(self.db).upload(
            FileUploadCommand(
                filename=PurePosixPath(avatar_object_name).name,
                content=content,
                content_type=content_type,
                object_name=avatar_object_name,
            )
        )
        async with transactional(self.db):
            await self.repo.update_avatar(session.account_id, uploaded_row["object_name"])
        await self._delete_previous_avatar(previous_avatar, uploaded_row["object_name"])
        return PortalUserCenterAvatarUpdateResult(
            avatar=uploaded_row["url"],
            file_id=uploaded_row["id"],
            object_name=uploaded_row["object_name"],
            url=uploaded_row["url"],
        )

    async def update_current_password(
        self,
        payload: PortalUserCenterPasswordUpdateCommand,
        session: SessionPayload,
    ) -> None:
        """校验旧密码/验证码后修改密码，并刷新账户会话。"""
        # 1. 加载账户与资料快照，校验改密方式
        account = await self.account_api.get_required(session.account_id)
        profile = await self.repo.get_by_account_id(session.account_id)
        if profile is not None:
            audit_snapshots.before_entity(profile)
        await verify_change_password(
            self.db,
            account=account,
            account_type=AccountType.PORTAL,
            old_password=payload.old_password,
            otp_code=payload.otp_code,
        )
        # 2. 校验新密码策略并落库，刷新在线会话
        async with transactional(self.db):
            await validate_and_record_password(
                self.db,
                session.account_id,
                payload.new_password,
                changed_by=session.account_id,
                change_reason="self_change",
                account_repo=self.account_api,
                password_port=self.password_port,
            )
            await self.account_api.update_password_hash(
                session.account_id,
                await hash_password_async(payload.new_password),
            )
        updated_profile = await self.repo.get_by_account_id(session.account_id)
        if updated_profile is not None:
            audit_snapshots.after_entity(updated_profile)
        await self._refresh_account_sessions(session.account_id)

    async def update_current_phone(
        self,
        payload: PortalUserCenterPhoneUpdateCommand,
        session: SessionPayload,
    ) -> None:
        """校验密码（绑定/换绑时另需 OTP）后更新当前账户手机号绑定。"""
        account = await self.account_api.get_required(session.account_id)
        await self._ensure_password(str(account.get("password_hash") or ""), payload.password)
        phone_value = str(payload.phone or "").strip()
        if phone_value:
            await self._consume_bind_code(
                AccountType.PORTAL, "PHONE", session.account_id, phone_value, payload.otp_code
            )
        profile = await self.repo.get_by_account_id(session.account_id)
        if payload.phone_login_enabled and not phone_value:
            raise BusinessError("Phone login requires a phone")
        async with transactional(self.db):
            await self.account_api.upsert_account_identity(
                session.account_id,
                AccountIdentityType.PHONE,
                payload.phone,
                enabled=payload.phone_login_enabled,
            )
            await self.repo.upsert(
                PortalProfileUpsertCommand(
                    account_id=session.account_id,
                    nickname=profile.get("nickname") if profile else None,
                    avatar=profile.get("avatar") if profile else None,
                    signature=profile.get("signature") if profile else None,
                    phone=payload.phone,
                    email=profile.get("email") if profile else None
                ).model_dump()
            )

    async def update_current_email(
        self,
        payload: PortalUserCenterEmailUpdateCommand,
        session: SessionPayload,
    ) -> None:
        """校验密码（绑定/换绑时另需 OTP）后更新当前账户邮箱绑定。"""
        account = await self.account_api.get_required(session.account_id)
        await self._ensure_password(str(account.get("password_hash") or ""), payload.password)
        email_value = str(payload.email or "").strip()
        if email_value:
            await self._consume_bind_code(
                AccountType.PORTAL, "EMAIL", session.account_id, email_value, payload.otp_code
            )
        profile = await self.repo.get_by_account_id(session.account_id)
        if payload.email_login_enabled and not email_value:
            raise BusinessError("Email login requires an email")
        async with transactional(self.db):
            await self.account_api.upsert_account_identity(
                session.account_id,
                AccountIdentityType.EMAIL,
                payload.email,
                enabled=payload.email_login_enabled,
            )
            await self.repo.upsert(
                PortalProfileUpsertCommand(
                    account_id=session.account_id,
                    nickname=profile.get("nickname") if profile else None,
                    avatar=profile.get("avatar") if profile else None,
                    signature=profile.get("signature") if profile else None,
                    phone=profile.get("phone") if profile else None,
                    email=payload.email
                ).model_dump()
            )

    async def _refresh_account_sessions(self, account_id: str) -> None:
        """刷新账户在线会话（改密/授权变更后）。"""
        await self._session_service.refresh_account_sessions(account_id)

    async def _consume_bind_code(
        self,
        account_type: AccountType,
        channel: str,
        account_id: str,
        target: str,
        otp_code: str | None,
    ) -> None:
        """校验绑定验证码（一次性消费）。"""
        await self._bind_code_port.consume_bind_code(
            account_type=account_type,
            channel=channel,
            account_id=account_id,
            target=target,
            code=otp_code,
        )

    async def _ensure_password(self, password_hash: str, password: str) -> None:
        """校验明文密码与哈希是否匹配，失败抛出 AuthenticationError。"""
        if not await verify_password_async(password, password_hash):
            raise AuthenticationError("Invalid account or password")

    def _normalize_avatar_content_type(self, content_type: str) -> str:
        """去除 content-type 中的参数（如 ; charset），并转为小写。"""
        return (content_type or "").split(";")[0].strip().lower()

    def _ensure_avatar_file(self, content: bytes, content_type: str) -> None:
        """校验头像文件非空、大小与类型合法。"""
        if not content:
            raise BusinessError("Avatar file is empty")
        if len(content) > AVATAR_MAX_SIZE:
            raise BusinessError("Avatar file must be 2MB or smaller")
        if content_type not in AVATAR_CONTENT_TYPES:
            raise BusinessError("Avatar file must be a JPEG, PNG, or WebP image")

    def _build_avatar_object_name(self, content_type: str) -> str:
        """按日期目录 + 随机名生成头像 object_name。"""
        now = datetime.now(UTC)
        extension = AVATAR_CONTENT_TYPES[content_type]
        return f"{now:%Y}/{now:%m}/{now:%d}/{uuid4().hex}{extension}"

    async def _delete_previous_avatar(
        self,
        previous_avatar: str | None,
        current_avatar: str,
    ) -> None:
        """删除被替换的旧头像文件（跳过空值、同对象与外部 URL）。"""
        previous_object_name = normalize_object_name(previous_avatar)
        current_object_name = normalize_object_name(current_avatar)
        if (
            not previous_object_name
            or previous_object_name == current_object_name
            or is_external_url(previous_object_name)
        ):
            return
        await FileService(self.db).delete_by_object_name(previous_object_name)

