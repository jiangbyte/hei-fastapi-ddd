""" Author: Charlie """

from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.iam.domain.enums import ResourceType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource, SysResourceModule


async def _seed_admin(client, token: str, permissions: list[str]) -> None:
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        db_session: AsyncSession = session
        account = SysAccount(
            password_hash="hashed",
            account_type=AccountType.ADMIN.value,
            account_status=AccountStatusEnum.ENABLED.value,
        )
        db_session.add(account)
        await db_session.flush()
        await session_store.set(
            SessionPayload(
                token=token,
                account_id=account.id,
                account_type=AccountType.ADMIN.value,
                permission_keys=permissions,
                permission_grants=[],
            ),
            ttl_seconds=3600,
        )
        await db_session.commit()
        return
    raise AssertionError("Expected test database session")


async def _seed_admin_and_portal_resources(client) -> None:
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        db_session: AsyncSession = session
        db_session.add_all(
            [
                SysResourceModule(
                    id="module_admin",
                    code="admin",
                    name="Admin",
                    client=AccountType.ADMIN.value,
                    sort=1,
                ),
                SysResourceModule(
                    id="module_portal",
                    code="portal",
                    name="Portal",
                    client=AccountType.PORTAL.value,
                    sort=2,
                ),
                SysResource(
                    id="resource_admin",
                    code="admin-resource",
                    name="Admin Resource",
                    resource_type=ResourceType.MENU.value,
                    module_id="module_admin",
                    path="/admin-resource",
                    component="/admin-resource/index.vue",
                    sort=1,
                ),
                SysResource(
                    id="resource_portal",
                    code="portal-resource",
                    name="Portal Resource",
                    resource_type=ResourceType.MENU.value,
                    module_id="module_portal",
                    path="/portal-resource",
                    component="/portal-resource/index.vue",
                    sort=2,
                ),
            ]
        )
        await db_session.commit()
        return
    raise AssertionError("Expected test database session")


async def test_admin_current_resources_only_return_admin_client_resources(client):
    token = "admin-current-resource-token"
    await _seed_admin(client, token, ["*:*:*"])
    await _seed_admin_and_portal_resources(client)

    response = await client.get(
        "/api/v1/admin/sys/resources/current",
        headers={"Authorization": token},
    )

    assert response.status_code == 200
    assert response.json()["code"] == "200"
    data = response.json()["data"]
    assert [item["id"] for item in data] == ["resource_admin"]
    assert data[0]["module_client"] == AccountType.ADMIN.value
    assert data[0]["module_id"] == "module_admin"


async def test_admin_resource_management_interfaces_keep_all_clients_by_default(client):
    token = "admin-resource-management-token"
    await _seed_admin(client, token, ["iam:resource:page", "iam:resource:list", "*:*:*"])
    await _seed_admin_and_portal_resources(client)
    headers = {"Authorization": token}

    page_response = await client.get(
        "/api/v1/admin/sys/resources/page?current=1&size=20",
        headers=headers,
    )
    tree_response = await client.get("/api/v1/admin/sys/resources/tree", headers=headers)

    assert page_response.status_code == 200
    assert tree_response.status_code == 200
    page_records = page_response.json()["data"]["records"]
    tree_records = tree_response.json()["data"]
    assert [item["id"] for item in page_records] == ["resource_admin", "resource_portal"]
    assert [item["id"] for item in tree_records] == ["resource_admin", "resource_portal"]
    assert {item["module_client"] for item in page_records} == {
        AccountType.ADMIN.value,
        AccountType.PORTAL.value,
    }


async def test_portal_current_resources_are_public(client):
    await _seed_admin_and_portal_resources(client)

    response = await client.get("/api/v1/portal/sys/resources/current")

    assert response.status_code == 200
    assert response.json()["code"] == "200"
    data = response.json()["data"]
    assert [item["id"] for item in data] == ["resource_portal"]
    assert data[0]["module_client"] == AccountType.PORTAL.value
    assert data[0]["module_id"] == "module_portal"
