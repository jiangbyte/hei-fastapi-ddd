""" Author: Charlie """

import re
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.iam.domain.enums import (
    AccountIdentityBindStatus,
    AccountIdentityType,
    RoleScopeType,
)
from hei_fastapi_ddd.contexts.iam.domain.role.constants import SUPER_ADMIN_ROLE_CODE
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import (
    SysAccount,
    SysAccountIdentity,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po import SysRole
from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.security.password import hash_password
from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store
from tests.iam_relation_helpers import account_role

_ADMIN_RESET_BASE = "http://admin.test/auth/forgot-password"
_PORTAL_RESET_BASE = "http://portal.test/auth/forgot-password"


@pytest.fixture(autouse=True)
def auth_security_bypass(monkeypatch):
    async def fake_verify_captcha(captcha_id: str, captcha_value: str) -> None:
        return None

    async def fake_decrypt_password(password_key_id: str, value: str | None) -> str:
        return value or ""

    monkeypatch.setattr("hei_fastapi_ddd.contexts.auth.trigger.http.auth_router.verify_captcha", fake_verify_captcha)
    monkeypatch.setattr("hei_fastapi_ddd.contexts.auth.trigger.http.auth_router.decrypt_password", fake_decrypt_password)
    config_reader._cache["AUTH_PASSWORD_RESET_URL_ADMIN"] = _ADMIN_RESET_BASE
    config_reader._cache["AUTH_PASSWORD_RESET_URL_PORTAL"] = _PORTAL_RESET_BASE


def _secured(payload: dict) -> dict:
    data = {
        **payload,
        "captcha_id": "captcha-test-id",
        "captcha_value": "ABCD",
    }
    if "password" in data:
        data["password_key_id"] = "password-key-test-id"
    return data


async def _seed_account(
    db_session: AsyncSession,
    *,
    identifier: str,
    password: str,
    account_type: AccountType,
) -> SysAccount:
    account = SysAccount(
        password_hash=hash_password(password),
        account_type=account_type.value,
        account_status=AccountStatusEnum.ENABLED.value,
    )
    db_session.add(account)
    await db_session.flush()
    db_session.add(
        SysAccountIdentity(
            account_id=account.id,
            identity_type=AccountIdentityType.ACCOUNT.value,
            identifier=identifier,
            verified=True,
            is_primary=True,
        )
    )
    return account


async def _add_identity(
    db_session: AsyncSession,
    account: SysAccount,
    identity_type: AccountIdentityType,
    identifier: str,
    verified: bool = True,
) -> None:
    db_session.add(
        SysAccountIdentity(
            account_id=account.id,
            identity_type=identity_type.value,
            identifier=identifier,
            verified=verified,
            is_primary=False,
            bind_status=AccountIdentityBindStatus.BOUND.value,
        )
    )


async def test_public_auth_login_route_not_found(client):
    response = await client.post(
        "/api/v1/public/auth/login",
        json={"account": "anyone", "password": "Secret@123"},
    )
        # 未注册的 /api 路径在路由前被 auth 白名单中间件拒绝。
    assert response.status_code == 401
    assert response.json()["code"] == "401"


async def test_portal_auth_login_success(client):
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        db_session: AsyncSession = session
        await _seed_account(
            db_session,
            identifier="portal_login_user",
            password="Portal@123456",
            account_type=AccountType.PORTAL,
        )
        await db_session.commit()
        break

    response = await client.post(
        "/api/v1/portal/login",
        json=_secured({"account": "portal_login_user", "password": "Portal@123456"}),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "200"
    data = payload["data"]
    assert data["account_type"] == AccountType.PORTAL.value


async def test_login_identity_type_is_strict(client):
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        db_session: AsyncSession = session
        account = await _seed_account(
            db_session,
            identifier="portal_identity_user",
            password="Portal@123456",
            account_type=AccountType.PORTAL,
        )
        await _add_identity(
            db_session,
            account,
            AccountIdentityType.EMAIL,
            "portal_identity@example.com",
        )
        await db_session.commit()
        break

    wrong_type_response = await client.post(
        "/api/v1/portal/login",
        json=_secured(
            {
                "account": "portal_identity_user",
                "password": "Portal@123456",
                "identity_type": "EMAIL",
            }
        ),
    )
    email_response = await client.post(
        "/api/v1/portal/login",
        json=_secured(
            {
                "account": "portal_identity@example.com",
                "password": "Portal@123456",
                "identity_type": "EMAIL",
            }
        ),
    )

    assert wrong_type_response.status_code == 401
    assert email_response.status_code == 200


async def test_admin_register_route_is_removed(client):
    response = await client.post(
        "/api/v1/admin/register",
        json=_secured(
            {
                "account": "admin_register_removed",
                "nickname": "Admin",
                "email": "admin-register@example.com",
                "password": "Admin@123456",
            }
        ),
    )

    assert response.status_code == 401
    assert response.json()["code"] == "401"


async def test_portal_register_requires_email_and_does_not_require_name_or_phone(client):
    missing_email = await client.post(
        "/api/v1/portal/register",
        json=_secured(
            {
                "register_channel": "ACCOUNT",
                "account": "portal_missing_email",
                "nickname": "Portal User",
                "password": "Portal@123456",
            }
        ),
    )
    created = await client.post(
        "/api/v1/portal/register",
        json=_secured(
            {
                "register_channel": "ACCOUNT",
                "account": "portal_register_email",
                "nickname": "Portal User",
                "email": "portal-register@example.com",
                "password": "Portal@123456",
            }
        ),
    )

    assert missing_email.status_code == 400
    assert created.status_code == 200
    assert created.json()["data"]["account_type"] == AccountType.PORTAL.value


async def test_admin_forgot_and_reset_password_use_email_link(client, monkeypatch):
    sent_messages: list[tuple[str, str, str]] = []

    async def fake_send_templated_mail(scene: str, to_email: str, variables: dict) -> None:
        body = str(variables.get("reset_link") or "")
        sent_messages.append((to_email, scene, body))

    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.auth.application.password_reset_service.send_templated_mail",
        fake_send_templated_mail,
    )

    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        db_session: AsyncSession = session
        account = await _seed_account(
            db_session,
            identifier="admin_reset_user",
            password="Admin@123456",
            account_type=AccountType.ADMIN,
        )
        await _add_identity(
            db_session,
            account,
            AccountIdentityType.EMAIL,
            "admin-reset@example.com",
        )
        await db_session.commit()
        break

    forgot = await client.post(
        "/api/v1/admin/forgot-password",
        json=_secured({"email": "admin-reset@example.com"}),
    )
    assert forgot.status_code == 200
    assert sent_messages and sent_messages[0][0] == "admin-reset@example.com"
    link = re.search(r"https?://\S+", sent_messages[0][2]).group(0)
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    token = query["token"][0]
    assert "email" not in query
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == _ADMIN_RESET_BASE

    reset = await client.post(
        "/api/v1/admin/reset-password",
        json=_secured(
            {
                "token": token,
                "password": "Admin@654321",
            }
        ),
    )
    login = await client.post(
        "/api/v1/admin/login",
        json=_secured(
            {
                "account": "admin-reset@example.com",
                "password": "Admin@654321",
                "identity_type": "EMAIL",
            }
        ),
    )
    reused = await client.post(
        "/api/v1/admin/reset-password",
        json=_secured(
            {
                "token": token,
                "password": "Admin@111111",
            }
        ),
    )

    assert reset.status_code == 200
    assert login.status_code == 200
    assert reused.status_code == 401


async def test_portal_forgot_password_uses_portal_reset_url(client, monkeypatch):
    sent_messages: list[str] = []

    async def fake_send_templated_mail(scene: str, to_email: str, variables: dict) -> None:
        sent_messages.append(str(variables.get("reset_link") or ""))

    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.auth.application.password_reset_service.send_templated_mail",
        fake_send_templated_mail,
    )

    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        db_session: AsyncSession = session
        account = await _seed_account(
            db_session,
            identifier="portal_reset_user",
            password="Portal@123456",
            account_type=AccountType.PORTAL,
        )
        await _add_identity(
            db_session,
            account,
            AccountIdentityType.EMAIL,
            "portal-reset@example.com",
        )
        await db_session.commit()
        break

    forgot = await client.post(
        "/api/v1/portal/forgot-password",
        json=_secured({"email": "portal-reset@example.com"}),
    )
    assert forgot.status_code == 200
    assert sent_messages
    link = re.search(r"https?://\S+", sent_messages[0]).group(0)
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    assert "email" not in query
    assert "token" in query
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == _PORTAL_RESET_BASE
    assert _ADMIN_RESET_BASE not in sent_messages[0]


async def test_logout_rejects_bearer_prefixed_token(client):
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        db_session: AsyncSession = session
        account = await _seed_account(
            db_session,
            identifier="portal_logout_user",
            password="Portal@123456",
            account_type=AccountType.PORTAL,
        )
        await session_store.set(
            SessionPayload(
                token="portal-raw-token",
                account_id=account.id,
                account_type=AccountType.PORTAL.value,
                role_ids=[],
                dept_ids=[],
                group_ids=[],
                permission_keys=[],
                permission_grants=[],
            ),
            ttl_seconds=3600,
        )
        await db_session.commit()
        break

    response = await client.post(
        "/api/v1/portal/logout",
        headers={"Authorization": "Bearer portal-raw-token"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "401"
    # Bearer 方案被忽略（非有效 HEI 会话传输）。
    assert response.json()["message"] == "Missing authorization token"


async def test_protected_admin_route_without_token_returns_401(client):
    response = await client.get("/api/v1/admin/sys/file/page")

    assert response.status_code == 401
    assert response.json()["code"] == "401"
    assert response.json()["message"] == "Missing authorization token"


async def test_protected_admin_route_with_invalid_token_returns_401(client):
    response = await client.get(
        "/api/v1/admin/sys/file/page",
        headers={"Authorization": "invalid-admin-token"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "401"
    assert response.json()["message"] == "Invalid or expired token"


async def test_admin_route_rejects_wrong_account_type_with_403(client):
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        db_session: AsyncSession = session
        account = await _seed_account(
            db_session,
            identifier="portal_account_type_user",
            password="Portal@123456",
            account_type=AccountType.PORTAL,
        )
        await session_store.set(
            SessionPayload(
                token="portal-account-type-token",
                account_id=account.id,
                account_type=AccountType.PORTAL.value,
                role_ids=[],
                dept_ids=[],
                group_ids=[],
                permission_keys=["sys:file:page"],
                permission_grants=[],
            ),
            ttl_seconds=3600,
        )
        await db_session.commit()
        break

    response = await client.get(
        "/api/v1/admin/sys/file/page",
        headers={"Authorization": "portal-account-type-token"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "403"
    assert response.json()["message"] == "Account type 'PORTAL' is not allowed"


async def test_admin_route_rejects_missing_permission_with_403(client):
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        db_session: AsyncSession = session
        account = SysAccount(
            password_hash=hash_password("Admin@123456"),
            account_type=AccountType.ADMIN.value,
            account_status=AccountStatusEnum.ENABLED.value,
        )
        db_session.add(account)
        await db_session.flush()
        await session_store.set(
            SessionPayload(
                token="admin-without-permission-token",
                account_id=account.id,
                account_type=AccountType.ADMIN.value,
                role_ids=[],
                dept_ids=[],
                group_ids=[],
                permission_keys=[],
                permission_grants=[],
            ),
            ttl_seconds=3600,
        )
        await db_session.commit()
        break

    response = await client.get(
        "/api/v1/admin/sys/file/page",
        headers={"Authorization": "admin-without-permission-token"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "403"
    assert response.json()["message"] == "Permission denied: sys:file:page"


async def test_admin_route_allows_valid_account_type_and_permission(client):
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        db_session: AsyncSession = session
        account = SysAccount(
            password_hash=hash_password("Admin@123456"),
            account_type=AccountType.ADMIN.value,
            account_status=AccountStatusEnum.ENABLED.value,
        )
        db_session.add(account)
        await db_session.flush()
        await session_store.set(
            SessionPayload(
                token="admin-with-permission-token",
                account_id=account.id,
                account_type=AccountType.ADMIN.value,
                role_ids=[],
                dept_ids=[],
                group_ids=[],
                permission_keys=["sys:file:page"],
                permission_grants=[],
            ),
            ttl_seconds=3600,
        )
        await db_session.commit()
        break

    response = await client.get(
        "/api/v1/admin/sys/file/page",
        headers={"Authorization": "admin-with-permission-token"},
    )

    assert response.status_code == 200
    assert response.json()["code"] == "200"


async def test_admin_route_allows_super_admin_role_without_explicit_permission(client):
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        db_session: AsyncSession = session
        account = await _seed_account(
            db_session,
            identifier="admin_super_role",
            password="Admin@123456",
            account_type=AccountType.ADMIN,
        )
        role = SysRole(
            code=SUPER_ADMIN_ROLE_CODE,
            name="Super Admin",
            category="SYSTEM",
            scope_type=RoleScopeType.PLATFORM.value,
            is_builtin=True,
        )
        db_session.add_all([account, role])
        await db_session.flush()
        db_session.add(account_role(account.id, role.id))
        await db_session.commit()
        break

    login_response = await client.post(
        "/api/v1/admin/login",
        json=_secured({"account": "admin_super_role", "password": "Admin@123456"}),
    )
    assert login_response.status_code == 200
    token = login_response.json()["data"]["token"]

    response = await client.get(
        "/api/v1/admin/sys/file/page",
        headers={"Authorization": token},
    )

    assert response.status_code == 200
    assert response.json()["code"] == "200"


async def test_login_validation_error_uses_unified_response(client):
    response = await client.post(
        "/api/v1/portal/login",
        json=_secured({"account": "ab", "password": "123"}),
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": "422",
        "message": "account: String should have at least 3 characters",
        "data": None,
    }
