""" Author: Charlie

管理端用户中心路由：当前账户信息、资料、头像、密码、手机与邮箱维护。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.shared.security.transport import decrypt_passwords
from hei_fastapi_ddd.shared.deps.auth import get_current_session, require_account_type
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.iam.application.account.query_service import AccountQueryService
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import AccountRepository
from hei_fastapi_ddd.contexts.profile.interfaces.http.admin_schemas import (
    AdminUserCenterAvatarUpdateResponse,
    AdminUserCenterEmailUpdateRequest,
    AdminUserCenterOrgInfoResponse,
    AdminUserCenterPasswordUpdateRequest,
    AdminUserCenterPhoneUpdateRequest,
    AdminUserCenterProfileUpdateRequest,
    ProfileUserAdminResponse,
)
from hei_fastapi_ddd.contexts.profile.application.admin.admin_application_service import AVATAR_MAX_SIZE, ProfileUserAdminService
from hei_fastapi_ddd.contexts.profile.interfaces.http.profile_schemas import AdminMeResponse, BindTargetRequest

router = APIRouter()


@router.get(
    "/v1/admin/me",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[AdminMeResponse],
)
async def get_me(
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[AdminMeResponse]:
    """查询当前管理端账户信息与组织归属。"""
    account_entity = await AccountRepository(db).get_required(session.account_id)
    account = (await AccountQueryService(db).build_account_schemas([account_entity]))[0]
    avatar = account.avatar
    (
        role_id_names,
        dept_id_names,
        group_id_names,
    ) = await ProfileUserAdminService(db).get_id_name_groups(
        session.role_ids,
        session.dept_ids,
        session.group_ids,
    )
    from hei_fastapi_ddd.contexts.auth.application.auth_application_service import AuthService
    from hei_fastapi_ddd.contexts.iam.application.account.password_helper import is_password_expired

    force_bind_email, force_bind_phone = await AuthService(db)._force_bind_flags(
        account_entity, AccountType.ADMIN
    )
    auth_service = AuthService(db)
    from hei_fastapi_ddd.contexts.profile.application.identity.identity_application_service import ProfileIdentityService

    identity = await ProfileIdentityService(db).get_user_status_for_account(session.account_id)
    return success(
        AdminMeResponse(
            account_id=session.account_id,
            account=account.account,
            account_type=AccountType(str(session.account_type)),
            nickname=account.nickname,
            avatar=avatar,
            role_ids=session.role_ids,
            dept_ids=session.dept_ids,
            group_ids=session.group_ids,
            role_id_names=role_id_names,
            dept_id_names=dept_id_names,
            group_id_names=group_id_names,
            permission_keys=session.permission_keys,
            password_expired=await is_password_expired(db, session.account_id),
            force_bind_email=force_bind_email,
            force_bind_phone=force_bind_phone,
            force_bind_identity=await auth_service.force_bind_identity_flag(
                session.account_id, AccountType.ADMIN
            ),
            identity=identity,
            profile=ProfileUserAdminResponse(
                account_id=session.account_id,
                nickname=account.nickname,
                avatar=avatar,
                signature=account.signature,
                phone=account.phone,
                email=account.email,
                phone_login_enabled=account.phone_login_enabled,
                email_login_enabled=account.email_login_enabled,
                remark=account.remark,
                created_at=account.created_at,
                updated_at=account.updated_at,
            ),
        )
    )


@router.post(
    "/v1/admin/profile/update",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[None],
)
async def update_user_center_profile(
    payload: AdminUserCenterProfileUpdateRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """更新当前管理端账户个人资料。"""
    await ProfileUserAdminService(db).update_current_profile(payload, session)
    return success()


@router.post(
    "/v1/admin/profile/avatar/upload",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[AdminUserCenterAvatarUpdateResponse],
)
async def upload_user_center_avatar(
    file: Annotated[UploadFile, File(...)],
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[AdminUserCenterAvatarUpdateResponse]:
    """上传并更新当前管理端账户头像。"""
    content = await file.read(AVATAR_MAX_SIZE + 1)
    return success(
        await ProfileUserAdminService(db).update_current_avatar(
            content=content,
            content_type=file.content_type or "",
            session=session,
        )
    )


@router.post(
    "/v1/admin/profile/password/send-code",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[None],
)
async def send_user_center_password_code(
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """向当前管理端账户发送改密验证码。"""
    from hei_fastapi_ddd.contexts.auth.application.password_change import send_change_password_code
    from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_repository import AccountRepository

    account = await AccountRepository(db).get_required(session.account_id)
    await send_change_password_code(
        db, account=account, account_type=AccountType.ADMIN
    )
    return success()


@router.post(
    "/v1/admin/profile/password/update",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[None],
)
async def update_user_center_password(
    payload: AdminUserCenterPasswordUpdateRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """修改当前管理端账户密码。"""
    old_password, new_password = await decrypt_passwords(
        payload.password_key_id,
        payload.old_password,
        payload.new_password,
    )
    await ProfileUserAdminService(db).update_current_password(
        payload.model_copy(
            update={
                "old_password": old_password,
                "new_password": new_password or "",
            }
        ),
        session,
    )
    return success()


@router.post(
    "/v1/admin/profile/phone/send-code",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[None],
)
async def send_user_center_phone_code(
    payload: BindTargetRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """向待绑定手机号发送验证码。"""
    from hei_fastapi_ddd.contexts.auth.application.auth_application_service import AuthService

    await AuthService(db).send_bind_code(
        account_type=AccountType.ADMIN,
        channel="PHONE",
        target=payload.target,
        account_id=session.account_id,
    )
    return success()


@router.post(
    "/v1/admin/profile/email/send-code",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[None],
)
async def send_user_center_email_code(
    payload: BindTargetRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """向待绑定邮箱发送验证码。"""
    from hei_fastapi_ddd.contexts.auth.application.auth_application_service import AuthService

    await AuthService(db).send_bind_code(
        account_type=AccountType.ADMIN,
        channel="EMAIL",
        target=payload.target,
        account_id=session.account_id,
    )
    return success()


@router.post(
    "/v1/admin/profile/phone/update",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[None],
)
async def update_user_center_phone(
    payload: AdminUserCenterPhoneUpdateRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """更新当前管理端账户手机号绑定。"""
    password = (await decrypt_passwords(payload.password_key_id, payload.password))[0]
    await ProfileUserAdminService(db).update_current_phone(
        payload.model_copy(update={"password": password or ""}),
        session,
    )
    return success()


@router.post(
    "/v1/admin/profile/email/update",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[None],
)
async def update_user_center_email(
    payload: AdminUserCenterEmailUpdateRequest,
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[None]:
    """更新当前管理端账户邮箱绑定。"""
    password = (await decrypt_passwords(payload.password_key_id, payload.password))[0]
    await ProfileUserAdminService(db).update_current_email(
        payload.model_copy(update={"password": password or ""}),
        session,
    )
    return success()


@router.get(
    "/v1/admin/profile/org-info",
    dependencies=[Depends(require_account_type(AccountType.ADMIN))],
    response_model=ApiResponse[AdminUserCenterOrgInfoResponse],
)
async def get_user_center_org_info(
    session: Annotated[SessionPayload, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[AdminUserCenterOrgInfoResponse]:
    """查询当前管理端账户的角色/部门/群组组织信息。"""
    return success(await ProfileUserAdminService(db).get_org_info(session))
