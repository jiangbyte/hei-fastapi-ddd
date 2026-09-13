""" Author: Charlie """

from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store


async def _seed_admin(client, token: str, permissions: list[str]) -> None:
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        account = SysAccount(
            password_hash="hashed",
            account_type=AccountType.ADMIN.value,
            account_status=AccountStatusEnum.ENABLED.value,
        )
        session.add(account)
        await session.flush()
        await session_store.set(
            SessionPayload(
                token=token,
                account_id=account.id,
                account_type=AccountType.ADMIN.value,
                role_ids=[],
                dept_ids=[],
                group_ids=[],
                permission_keys=permissions,
                permission_grants=[],
            ),
            ttl_seconds=3600,
        )
        await session.commit()
        break


def _payload(**overrides):
    data = {
        "title": "Home Banner",
        "image": "https://example.com/banner.png",
        "url": "https://example.com",
        "link_type": "URL",
        "summary": "Summary",
        "description": "Description",
        "category": "HOME",
        "type": "CAROUSEL",
        "position": "HOME_TOP",
        "target_account_types": ["PORTAL"],
        "sort": 1,
        "status": "ENABLED",
    }
    data.update(overrides)
    return data


async def _banner_ids_by_title(client, headers: dict[str, str]) -> dict[str, str]:
    response = await client.get(
        "/api/v1/admin/sys/banners/page?current=1&size=20&target_account_type=PORTAL&position=HOME_TOP",
        headers=headers,
    )
    assert response.status_code == 200
    return {item["title"]: item["id"] for item in response.json()["data"]["records"]}


async def test_admin_banner_create_page_detail_update_delete(client):
    token = "admin-banner-token"
    await _seed_admin(
        client,
        token,
        [
            "sys:banner:create",
            "sys:banner:page",
            "sys:banner:detail",
            "sys:banner:update",
            "sys:banner:delete",
        ],
    )
    headers = {"Authorization": token}

    create_response = await client.post(
        "/api/v1/admin/sys/banners/create",
        headers=headers,
        json=_payload(),
    )
    assert create_response.status_code == 200
    assert create_response.json()["data"] is None

    page_response = await client.get(
        "/api/v1/admin/sys/banners/page?current=1&size=20&target_account_type=PORTAL&position=HOME_TOP",
        headers=headers,
    )
    assert page_response.status_code == 200
    assert page_response.json()["data"]["total"] == "1"
    banner_id = page_response.json()["data"]["records"][0]["id"]
    assert page_response.json()["data"]["records"][0]["target_account_types"] == ["PORTAL"]

    detail_response = await client.get(
        f"/api/v1/admin/sys/banners/detail?id={banner_id}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["title"] == "Home Banner"
    assert detail_response.json()["data"]["target_account_types"] == ["PORTAL"]

    update_response = await client.post(
        "/api/v1/admin/sys/banners/update",
        headers=headers,
        json=_payload(id=banner_id, title="Updated Banner"),
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"] is None
    updated_detail_response = await client.get(
        f"/api/v1/admin/sys/banners/detail?id={banner_id}",
        headers=headers,
    )
    assert updated_detail_response.json()["data"]["title"] == "Updated Banner"

    delete_response = await client.post(
        "/api/v1/admin/sys/banners/delete",
        headers=headers,
        json={"ids": [banner_id]},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["data"] is None


async def test_admin_banner_delete_accepts_id_array(client):
    token = "admin-banner-batch-delete-token"
    await _seed_admin(client, token, ["sys:banner:create", "sys:banner:page", "sys:banner:delete"])
    headers = {"Authorization": token}
    first = await client.post(
        "/api/v1/admin/sys/banners/create",
        headers=headers,
        json=_payload(title="First Banner"),
    )
    second = await client.post(
        "/api/v1/admin/sys/banners/create",
        headers=headers,
        json=_payload(title="Second Banner", sort=2),
    )
    assert first.json()["data"] is None
    assert second.json()["data"] is None
    ids_by_title = await _banner_ids_by_title(client, headers)
    first_id = ids_by_title["First Banner"]
    second_id = ids_by_title["Second Banner"]

    response = await client.post(
        "/api/v1/admin/sys/banners/delete",
        headers=headers,
        json={"ids": [first_id, second_id]},
    )

    assert response.status_code == 200
    assert response.json()["data"] is None

    page_response = await client.get(
        "/api/v1/admin/sys/banners/page?current=1&size=20&target_account_type=PORTAL&position=HOME_TOP",
        headers=headers,
    )
    assert page_response.json()["data"]["total"] == "0"


async def test_public_banner_list_does_not_require_admin_session(client):
    token = "admin-banner-public-seed-token"
    await _seed_admin(client, token, ["sys:banner:create"])
    create_response = await client.post(
        "/api/v1/admin/sys/banners/create",
        headers={"Authorization": token},
        json=_payload(title="Public Banner"),
    )
    assert create_response.json()["data"] is None

    response = await client.get("/api/v1/portal/sys/banners/list?position=HOME_TOP")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "200"
    assert [item["title"] for item in payload["data"]] == ["Public Banner"]


async def test_admin_banner_page_without_permission_returns_403(client):
    token = "admin-banner-no-permission-token"
    await _seed_admin(client, token, [])

    response = await client.get(
        "/api/v1/admin/sys/banners/page",
        headers={"Authorization": token},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "403"
    assert response.json()["message"] == "Permission denied: sys:banner:page"


async def test_admin_banner_list_returns_admin_target_only(client):
    token = "admin-banner-list-token"
    await _seed_admin(client, token, ["sys:banner:create"])
    headers = {"Authorization": token}

    portal = await client.post(
        "/api/v1/admin/sys/banners/create",
        headers=headers,
        json=_payload(title="Portal Only", target_account_types=["PORTAL"], position="HOME_TOP"),
    )
    admin = await client.post(
        "/api/v1/admin/sys/banners/create",
        headers=headers,
        json=_payload(
            title="Admin Carousel",
            target_account_types=["ADMIN"],
            position="ADMIN_TOP",
        ),
    )
    assert portal.json()["data"] is None
    assert admin.json()["data"] is None

    response = await client.get(
        "/api/v1/admin/sys/banners/list?position=ADMIN_TOP",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["code"] == "200"
    assert [item["title"] for item in response.json()["data"]] == ["Admin Carousel"]
