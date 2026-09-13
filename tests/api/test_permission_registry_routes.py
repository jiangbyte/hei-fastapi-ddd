""" Author: Charlie """

async def test_subject_permission_grant_routes_are_not_registered(client):
    routes = [
        ("GET", "/api/v1/admin/sys/accounts/own-permission"),
        ("GET", "/api/v1/admin/sys/accounts/own-permission-detail"),
        ("POST", "/api/v1/admin/sys/accounts/grant-permission"),
        ("GET", "/api/v1/admin/sys/roles/permission-tree-selector"),
        ("GET", "/api/v1/admin/sys/roles/own-permission"),
        ("GET", "/api/v1/admin/sys/roles/own-permission-detail"),
        ("POST", "/api/v1/admin/sys/roles/grant-permission"),
        ("GET", "/api/v1/admin/sys/groups/own-permission"),
        ("GET", "/api/v1/admin/sys/groups/own-permission-detail"),
        ("POST", "/api/v1/admin/sys/groups/grant-permission"),
    ]

    for method, path in routes:
        response = await client.request(method, path)
        # 未注册的 /api 路径在路由前被 auth 白名单中间件拒绝。
        assert response.status_code == 401


async def test_generic_grant_routes_are_not_registered(client):
    response = await client.post(
        "/api/v1/admin/resource-grants",
        json={},
    )

    assert response.status_code == 401
