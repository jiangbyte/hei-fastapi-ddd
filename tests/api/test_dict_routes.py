""" Author: Charlie """

from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType
from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.dict_po import SysDict


async def _seed_admin(client, token: str, permissions: list[str]) -> str:
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        account = SysAccount(
            password_hash="hashed",
            account_type=AccountType.ADMIN.value,
            account_status=AccountStatusEnum.ENABLED.value,
        )
        session.add(account)
        await session.flush()
        account_id = account.id
        await session_store.set(
            SessionPayload(
                token=token,
                account_id=account_id,
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
        return account_id
    raise RuntimeError("Database session override is unavailable")


def _payload(**overrides):
    data = {
        "code": "PROFILE_GENDER",
        "label": "Gender",
        "value": "gender",
        "color": "#1677ff",
        "category": "BIZ",
        "sort": 1,
        "status": "ENABLED",
    }
    data.update(overrides)
    return data


async def _dict_record_by_code(client, headers: dict[str, str], code: str):
    response = await client.get(
        f"/api/v1/admin/sys/dicts/page?current=1&size=20&code={code}",
        headers=headers,
    )
    assert response.status_code == 200
    records = response.json()["data"]["records"]
    assert records
    return records[0]


async def test_admin_dict_create_page_detail_update_delete(client):
    token = "admin-dict-token"
    admin_id = await _seed_admin(
        client,
        token,
        [
            "sys:dict:create",
            "sys:dict:page",
            "sys:dict:detail",
            "sys:dict:update",
            "sys:dict:delete",
        ],
    )
    headers = {"Authorization": token}

    create_response = await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers=headers,
        json=_payload(),
    )
    assert create_response.status_code == 200
    assert create_response.json()["data"] is None

    page_response = await client.get(
        "/api/v1/admin/sys/dicts/page?current=1&size=20&category=BIZ&status=ENABLED",
        headers=headers,
    )
    assert page_response.status_code == 200
    assert page_response.json()["data"]["total"] == "1"
    dict_id = page_response.json()["data"]["records"][0]["id"]

    detail_response = await client.get(
        f"/api/v1/admin/sys/dicts/detail?id={dict_id}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["code"] == "PROFILE_GENDER"
    assert detail_response.json()["data"]["created_by"] == admin_id
    assert detail_response.json()["data"]["updated_by"] == admin_id

    update_response = await client.post(
        "/api/v1/admin/sys/dicts/update",
        headers=headers,
        json=_payload(id=dict_id, label="Gender Updated", status="DISABLED"),
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"] is None
    updated_detail_response = await client.get(
        f"/api/v1/admin/sys/dicts/detail?id={dict_id}",
        headers=headers,
    )
    assert updated_detail_response.json()["data"]["label"] == "Gender Updated"
    assert updated_detail_response.json()["data"]["created_by"] == admin_id
    assert updated_detail_response.json()["data"]["updated_by"] == admin_id

    delete_response = await client.post(
        "/api/v1/admin/sys/dicts/delete",
        headers=headers,
        json={"ids": [dict_id]},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["data"] is None


async def test_admin_dict_tree_supports_optional_category(client):
    token = "admin-dict-tree-token"
    await _seed_admin(client, token, ["sys:dict:create", "sys:dict:page", "sys:dict:tree"])
    headers = {"Authorization": token}

    root_response = await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers=headers,
        json=_payload(code="PROFILE_GENDER", label="Gender", sort=1),
    )
    assert root_response.json()["data"] is None
    root_id = (await _dict_record_by_code(client, headers, "PROFILE_GENDER"))["id"]
    await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers=headers,
        json=_payload(
            code="PROFILE_GENDER_MALE",
            label="Male",
            value="M",
            parent_id=root_id,
            sort=2,
        ),
    )
    await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers=headers,
        json=_payload(code="ORDER_STATUS", label="Order Status", category="SYS", sort=3),
    )

    profile_response = await client.get(
        "/api/v1/admin/sys/dicts/tree?category=BIZ",
        headers=headers,
    )
    all_response = await client.get("/api/v1/admin/sys/dicts/tree", headers=headers)

    assert profile_response.status_code == 200
    assert [node["code"] for node in profile_response.json()["data"]] == ["PROFILE_GENDER"]
    assert profile_response.json()["data"][0]["children"][0]["code"] == "PROFILE_GENDER_MALE"
    assert all_response.status_code == 200
    assert [node["code"] for node in all_response.json()["data"]] == [
        "PROFILE_GENDER",
        "ORDER_STATUS",
    ]


async def test_portal_dict_tree_is_public(client):
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        session.add(
            SysDict(
                id="portal_dict_status",
                code="COMMON_STATUS",
                label="Common Status",
                value="common_status",
                category="SYS",
                sort=1,
            )
        )
        await session.commit()
        break

    response = await client.get("/api/v1/portal/sys/dicts/tree")

    assert response.status_code == 200
    assert response.json()["code"] == "200"
    assert [node["code"] for node in response.json()["data"]] == ["COMMON_STATUS"]


async def test_admin_dict_page_detail_tree_include_parent_id_name(client):
    token = "admin-dict-parent-name-token"
    await _seed_admin(
        client,
        token,
        ["sys:dict:create", "sys:dict:page", "sys:dict:detail", "sys:dict:tree"],
    )
    headers = {"Authorization": token}

    parent_response = await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers=headers,
        json=_payload(code="REGION", label="Region", sort=1),
    )
    assert parent_response.json()["data"] is None
    parent_id = (await _dict_record_by_code(client, headers, "REGION"))["id"]
    child_response = await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers=headers,
        json=_payload(code="REGION_CN", label="China", parent_id=parent_id, sort=2),
    )
    assert child_response.json()["data"] is None
    child_id = (await _dict_record_by_code(client, headers, "REGION_CN"))["id"]

    page_response = await client.get(
        "/api/v1/admin/sys/dicts/page?current=1&size=20&category=BIZ",
        headers=headers,
    )
    detail_response = await client.get(
        f"/api/v1/admin/sys/dicts/detail?id={child_id}",
        headers=headers,
    )
    tree_response = await client.get(
        "/api/v1/admin/sys/dicts/tree?category=BIZ",
        headers=headers,
    )

    assert page_response.status_code == 200
    page_records = {item["id"]: item for item in page_response.json()["data"]["records"]}
    assert page_records[parent_id]["parent_id_name"] is None
    assert page_records[child_id]["parent_id_name"] == "Region"
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["parent_id_name"] == "Region"
    assert tree_response.status_code == 200
    assert tree_response.json()["data"][0]["children"][0]["parent_id_name"] == "Region"


async def test_admin_dict_page_parent_filter_matches_direct_children_only(client):
    token = "admin-dict-parent-filter-token"
    await _seed_admin(client, token, ["sys:dict:create", "sys:dict:page"])
    headers = {"Authorization": token}

    parent_response = await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers=headers,
        json=_payload(code="COMMON_STATUS", label="Common Status", sort=1),
    )
    assert parent_response.json()["data"] is None
    parent_id = (await _dict_record_by_code(client, headers, "COMMON_STATUS"))["id"]
    enabled_response = await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers=headers,
        json=_payload(
            code="COMMON_STATUS_ENABLED",
            label="Enabled",
            parent_id=parent_id,
            sort=2,
        ),
    )
    assert enabled_response.json()["data"] is None
    enabled_id = (await _dict_record_by_code(client, headers, "COMMON_STATUS_ENABLED"))["id"]
    disabled_response = await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers=headers,
        json=_payload(
            code="COMMON_STATUS_DISABLED",
            label="Disabled",
            parent_id=parent_id,
            sort=3,
        ),
    )
    assert disabled_response.json()["data"] is None
    disabled_id = (await _dict_record_by_code(client, headers, "COMMON_STATUS_DISABLED"))["id"]
    await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers=headers,
        json=_payload(
            code="COMMON_STATUS_ENABLED_CHILD",
            label="Enabled Child",
            parent_id=enabled_id,
            sort=4,
        ),
    )

    page_response = await client.get(
        f"/api/v1/admin/sys/dicts/page?current=1&size=20&category=BIZ&parent_id={parent_id}",
        headers=headers,
    )

    assert page_response.status_code == 200
    data = page_response.json()["data"]
    # 对齐 hei-boot：parent_id 仅精确匹配直接子节点（不含父节点自身）。
    assert data["total"] == "2"
    assert {item["id"] for item in data["records"]} == {enabled_id, disabled_id}


async def test_admin_dict_page_without_permission_returns_403(client):
    token = "admin-dict-no-permission-token"
    await _seed_admin(client, token, [])

    response = await client.get(
        "/api/v1/admin/sys/dicts/page",
        headers={"Authorization": token},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "403"
    assert response.json()["message"] == "Permission denied: sys:dict:page"


async def test_admin_dict_rejects_invalid_code(client):
    token = "admin-dict-invalid-code-token"
    await _seed_admin(client, token, ["sys:dict:create"])

    response = await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers={"Authorization": token},
        json=_payload(code="COMMON-STATUS"),
    )

    assert response.status_code == 422


async def test_admin_dict_rejects_non_standard_category(client):
    token = "admin-dict-invalid-category-token"
    await _seed_admin(client, token, ["sys:dict:create"])

    response = await client.post(
        "/api/v1/admin/sys/dicts/create",
        headers={"Authorization": token},
        json=_payload(category="OTHER"),
    )

    assert response.status_code == 422
