""" Author: Charlie """

import uuid

import pytest

from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType, StatusEnum
from hei_fastapi_ddd.shared.exceptions.business import ConflictError
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.iam.domain.enums import GrantSubjectType, ResourceType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource, SysResourceModule
from hei_fastapi_ddd.contexts.iam.interfaces.http.resource_schemas import (
    ResourceCreateRequest,
    ResourceModuleAdminPageQuery,
    ResourceTreeQuery,
    ResourceUpdateRequest,
)
from hei_fastapi_ddd.contexts.iam.application.resource.resource_application_service import ResourceModuleService, ResourceService
from tests.iam_relation_helpers import subject_resource_grant


def _session(account_id: str, permission_keys: list[str]) -> SessionPayload:
    return SessionPayload(
        token=f"{account_id}-token",
        account_id=account_id,
        account_type=AccountType.ADMIN.value,
        permission_keys=permission_keys,
    )


async def test_current_resources_super_permission_returns_all_enabled_resources(db_session):
    db_session.add_all(
        [
            SysResource(
                id="resource_root",
                code="root",
                name="Root",
                resource_type=ResourceType.CATALOG.value,
                sort=1,
            ),
            SysResource(
                id="resource_child",
                parent_id="resource_root",
                code="child",
                name="Child",
                resource_type=ResourceType.MENU.value,
                sort=2,
            ),
            SysResource(
                id="resource_disabled",
                code="disabled",
                name="Disabled",
                resource_type=ResourceType.MENU.value,
                status=StatusEnum.DISABLED.value,
                sort=3,
            ),
        ]
    )
    await db_session.commit()

    resources = await ResourceService(db_session).list_current_resources(
        _session("admin", ["*:*:*"])
    )

    assert [resource.id for resource in resources] == ["resource_root", "resource_child"]


async def test_resource_code_is_unique_within_module_for_create_and_update(db_session):
    db_session.add_all(
        [
            SysResourceModule(
                id="module_a",
                code="module-a",
                name="Module A",
            ),
            SysResourceModule(
                id="module_b",
                code="module-b",
                name="Module B",
            ),
        ]
    )
    await db_session.commit()

    service = ResourceService(db_session)
    await service.create(
        ResourceCreateRequest(
            code="shared-code",
            name="Resource A",
            resource_type=ResourceType.MENU,
            module_id="module_a",
            sort=1,
        )
    )
    await service.create(
        ResourceCreateRequest(
            code="shared-code",
            name="Resource B",
            resource_type=ResourceType.MENU,
            module_id="module_b",
            sort=1,
        )
    )
    await db_session.commit()

    with pytest.raises(ConflictError, match="Resource code already exists in module"):
        await service.create(
            ResourceCreateRequest(
                code="shared-code",
                name="Duplicate",
                resource_type=ResourceType.MENU,
                module_id="module_a",
                sort=2,
            )
        )

    resources = await service.repo.list_resources(module_id="module_a")
    current = resources[0]
    await service.update(
        ResourceUpdateRequest(
            id=current.id,
            code=current.code,
            name="Resource A Updated",
            resource_type=ResourceType.MENU,
            module_id=current.module_id,
            sort=current.sort,
        )
    )
    await db_session.commit()

    await service.create(
        ResourceCreateRequest(
            code="other-code",
            name="Other",
            resource_type=ResourceType.MENU,
            module_id="module_a",
            sort=3,
        )
    )
    await db_session.commit()

    with pytest.raises(ConflictError, match="Resource code already exists in module"):
        await service.update(
            ResourceUpdateRequest(
                id=current.id,
                code="other-code",
                name="Resource A Updated",
                resource_type=ResourceType.MENU,
                module_id=current.module_id,
                sort=current.sort,
            )
        )


async def test_resource_module_move_checks_descendant_code_conflicts(db_session):
    db_session.add_all(
        [
            SysResourceModule(
                id="module_a",
                code="module-a",
                name="Module A",
            ),
            SysResourceModule(
                id="module_b",
                code="module-b",
                name="Module B",
            ),
            SysResource(
                id="resource_root",
                code="root",
                name="Root",
                resource_type=ResourceType.CATALOG.value,
                module_id="module_a",
                sort=1,
            ),
            SysResource(
                id="resource_child",
                parent_id="resource_root",
                code="duplicate-child",
                name="Child",
                resource_type=ResourceType.MENU.value,
                module_id="module_a",
                sort=1,
            ),
            SysResource(
                id="resource_existing",
                code="duplicate-child",
                name="Existing",
                resource_type=ResourceType.MENU.value,
                module_id="module_b",
                sort=1,
            ),
        ]
    )
    await db_session.commit()

    with pytest.raises(ConflictError, match="Resource code already exists in module"):
        await ResourceService(db_session).update(
            ResourceUpdateRequest(
                id="resource_root",
                code="root",
                name="Root",
                resource_type=ResourceType.CATALOG,
                module_id="module_b",
                sort=1,
            )
        )


async def test_current_resources_regular_account_returns_granted_resources_with_parents(db_session):
    db_session.add_all(
        [
            SysAccount(
                id="account_1",
                password_hash="x",
                account_type=AccountType.ADMIN.value,
                account_status=AccountStatusEnum.ENABLED.value,
            ),
            SysResourceModule(
                id="module_iam",
                code="iam",
                name="IAM",
            ),
            SysResource(
                id="resource_root",
                code="root",
                name="Root",
                resource_type=ResourceType.CATALOG.value,
                module_id="module_iam",
                sort=1,
            ),
            SysResource(
                id="resource_granted",
                parent_id="resource_root",
                code="granted",
                name="Granted",
                resource_type=ResourceType.MENU.value,
                module_id="module_iam",
                path="/iam/granted",
                component="/iam/granted/index.vue",
                sort=2,
            ),
            SysResource(
                id="resource_other",
                parent_id="resource_root",
                code="other",
                name="Other",
                resource_type=ResourceType.MENU.value,
                sort=3,
            ),
            subject_resource_grant(
                GrantSubjectType.ACCOUNT,
                "account_1",
                "resource_granted",
                account_type=AccountType.ADMIN.value,
            ),
        ]
    )
    await db_session.commit()

    resources = await ResourceService(db_session).list_current_resources(
        _session("account_1", ["iam:resource:list"])
    )
    tree = await ResourceService(db_session).list_resource_tree(
        _session("account_1", ["iam:resource:list"]),
        ResourceTreeQuery(),
    )

    assert [resource.id for resource in resources] == ["resource_root", "resource_granted"]
    assert [node.id for node in tree] == ["resource_root"]
    assert [node.id for node in tree[0].children] == ["resource_granted"]
    assert tree[0].children[0].parent_id == "resource_root"
    assert tree[0].children[0].module_id == "module_iam"
    assert tree[0].children[0].module_id_name == "IAM"
    assert tree[0].children[0].path == "/iam/granted"
    assert tree[0].children[0].component == "/iam/granted/index.vue"
    assert tree[0].children[0].status == StatusEnum.ENABLED.value


async def test_resource_tree_regular_account_without_grants_returns_empty(db_session):
    db_session.add(
        SysResource(
            id="resource_root",
            code="root",
            name="Root",
            resource_type=ResourceType.CATALOG.value,
        )
    )
    await db_session.commit()

    tree = await ResourceService(db_session).list_resource_tree(
        _session("account_without_grant", ["iam:resource:list"]),
        ResourceTreeQuery(),
    )

    assert tree == []


async def test_current_resources_filters_by_portal_module_client(db_session):
    db_session.add_all(
        [
            SysResourceModule(
                id="module_admin",
                code="admin",
                name="Admin",
                client=AccountType.ADMIN.value,
            ),
            SysResourceModule(
                id="module_portal",
                code="portal",
                name="Portal",
                client=AccountType.PORTAL.value,
            ),
            SysResource(
                id="resource_admin",
                code="admin-resource",
                name="Admin Resource",
                resource_type=ResourceType.MENU.value,
                module_id="module_admin",
                sort=1,
            ),
            SysResource(
                id="resource_portal",
                code="portal-resource",
                name="Portal Resource",
                resource_type=ResourceType.MENU.value,
                module_id="module_portal",
                sort=2,
            ),
        ]
    )
    await db_session.commit()

    resources = await ResourceService(db_session).list_current_resources(
        _session("portal", ["*:*:*"]),
        module_client=AccountType.PORTAL,
    )

    assert [resource.id for resource in resources] == ["resource_portal"]
    assert resources[0].module_client == AccountType.PORTAL.value


async def test_current_resource_modules_group_admin_resources(db_session):
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
                code="HEADER",
                name="Header",
                client=AccountType.PORTAL.value,
                sort=2,
            ),
            SysResource(
                id="resource_admin",
                code="admin-resource",
                name="Admin Resource",
                resource_type=ResourceType.MENU.value,
                module_id="module_admin",
                sort=1,
            ),
            SysResource(
                id="resource_portal",
                code="portal-resource",
                name="Portal Resource",
                resource_type=ResourceType.MENU.value,
                module_id="module_portal",
                sort=2,
            ),
        ]
    )
    await db_session.commit()

    resources = await ResourceService(db_session).list_current_resources(
        _session("admin", ["*:*:*"]),
        module_client=AccountType.ADMIN,
    )

    assert [resource.id for resource in resources] == ["resource_admin"]
    assert resources[0].module_client == AccountType.ADMIN.value


async def test_public_portal_resources_return_enabled_portal_resources_without_session(db_session):
    db_session.add_all(
        [
            SysResourceModule(
                id="module_admin",
                code="admin",
                name="Admin",
                client=AccountType.ADMIN.value,
            ),
            SysResourceModule(
                id="module_portal",
                code="portal",
                name="Portal",
                client=AccountType.PORTAL.value,
            ),
            SysResource(
                id="resource_admin",
                code="admin-resource",
                name="Admin Resource",
                resource_type=ResourceType.MENU.value,
                module_id="module_admin",
                sort=1,
            ),
            SysResource(
                id="resource_portal",
                code="portal-resource",
                name="Portal Resource",
                resource_type=ResourceType.MENU.value,
                module_id="module_portal",
                sort=2,
            ),
            SysResource(
                id="resource_portal_disabled",
                code="portal-disabled-resource",
                name="Portal Disabled Resource",
                resource_type=ResourceType.MENU.value,
                module_id="module_portal",
                status=StatusEnum.DISABLED.value,
                sort=3,
            ),
        ]
    )
    await db_session.commit()

    resources = await ResourceService(db_session).list_public_portal_resources()

    assert [resource.id for resource in resources] == ["resource_portal"]
    assert resources[0].module_client == AccountType.PORTAL.value


async def test_public_portal_resource_modules_group_resources(db_session):
    db_session.add_all(
        [
            SysResourceModule(
                id="module_header",
                code="HEADER",
                name="Header",
                client=AccountType.PORTAL.value,
                sort=1,
            ),
            SysResourceModule(
                id="module_content",
                code="CONTENT",
                name="Content",
                client=AccountType.PORTAL.value,
                sort=2,
            ),
            SysResource(
                id="resource_header",
                code="header-resource",
                name="Header Resource",
                resource_type=ResourceType.MENU.value,
                module_id="module_header",
                sort=1,
            ),
            SysResource(
                id="resource_content",
                code="content-resource",
                name="Content Resource",
                resource_type=ResourceType.MENU.value,
                module_id="module_content",
                sort=2,
            ),
        ]
    )
    await db_session.commit()

    resources = await ResourceService(db_session).list_public_portal_resources()

    assert sorted([resource.id for resource in resources]) == [
        "resource_content",
        "resource_header",
    ]


async def test_resource_tree_filters_by_module_id_and_client(db_session):
    db_session.add_all(
        [
            SysResourceModule(
                id="module_admin_a",
                code="admin-a",
                name="Admin A",
                client=AccountType.ADMIN.value,
                sort=1,
            ),
            SysResourceModule(
                id="module_admin_b",
                code="admin-b",
                name="Admin B",
                client=AccountType.ADMIN.value,
                sort=2,
            ),
            SysResource(
                id="resource_admin_a",
                code="admin-a-root",
                name="Admin A Root",
                resource_type=ResourceType.CATALOG.value,
                module_id="module_admin_a",
                sort=1,
            ),
            SysResource(
                id="resource_admin_b",
                code="admin-b-root",
                name="Admin B Root",
                resource_type=ResourceType.CATALOG.value,
                module_id="module_admin_b",
                sort=2,
            ),
        ]
    )
    await db_session.commit()

    tree = await ResourceService(db_session).list_resource_tree(
        _session("admin", ["*:*:*"]),
        ResourceTreeQuery(
            module_id="module_admin_b",
            module_client=AccountType.ADMIN,
        ),
    )

    assert [node.id for node in tree] == ["resource_admin_b"]
    assert tree[0].module_id_name == "Admin B"
    assert tree[0].module_client == AccountType.ADMIN.value


async def test_resource_module_selector_and_page_filter_by_client(db_session):
    suffix = uuid.uuid4().hex[:8]
    admin_module_id = f"module_admin_{suffix}"
    portal_module_id = f"module_portal_{suffix}"
    db_session.add_all(
        [
            SysResourceModule(
                id=admin_module_id,
                code=f"admin_{suffix}",
                name="Admin",
                client=AccountType.ADMIN.value,
                sort=1,
            ),
            SysResourceModule(
                id=portal_module_id,
                code=f"portal_{suffix}",
                name="Portal",
                client=AccountType.PORTAL.value,
                sort=2,
            ),
        ]
    )
    await db_session.commit()

    service = ResourceModuleService(db_session)
    selector = await service.selector()
    selector_ids = {item.id for item in selector}
    page = await service.page_admin(
        ResourceModuleAdminPageQuery(
            current=1, size=20, client=AccountType.PORTAL,
        )
    )

    assert portal_module_id in selector_ids
    assert [item.id for item in page.records] == [portal_module_id]


async def test_grant_modules_group_by_real_parent_without_root(db_session):
    suffix = uuid.uuid4().hex[:8]
    module_id = f"module_admin_{suffix}"
    db_session.add_all(
        [
            SysResourceModule(
                id=module_id,
                code=f"admin_{suffix}",
                name="Admin",
                client=AccountType.ADMIN.value,
                sort=1,
            ),
            SysResource(
                id=f"catalog_sys_{suffix}",
                code=f"sys_{suffix}",
                name="系统",
                resource_type=ResourceType.CATALOG.value,
                module_id=module_id,
                sort=1,
            ),
            SysResource(
                id=f"menu_banner_{suffix}",
                parent_id=f"catalog_sys_{suffix}",
                code=f"sys-banner_{suffix}",
                name="展示图管理",
                resource_type=ResourceType.MENU.value,
                module_id=module_id,
                sort=2,
            ),
            SysResource(
                id=f"page_banner_create_{suffix}",
                parent_id=f"menu_banner_{suffix}",
                code=f"sys-banner-create-page_{suffix}",
                name="新增展示图页",
                resource_type=ResourceType.PAGE.value,
                module_id=module_id,
                sort=3,
            ),
            SysResource(
                id=f"menu_dashboard_{suffix}",
                code=f"dashboard_{suffix}",
                name="运营工作台",
                resource_type=ResourceType.MENU.value,
                module_id=module_id,
                sort=4,
            ),
        ]
    )
    await db_session.commit()

    modules = await ResourceService(db_session).list_grant_modules(
        module_client=AccountType.ADMIN,
    )
    assert len(modules) == 1
    menu_by_id = {item.id: item for item in modules[0].menu}

    menu_banner_id = f"menu_banner_{suffix}"
    page_banner_create_id = f"page_banner_create_{suffix}"
    menu_dashboard_id = f"menu_dashboard_{suffix}"
    assert set(menu_by_id) == {menu_banner_id, page_banner_create_id, menu_dashboard_id}
    assert f"catalog_sys_{suffix}" not in menu_by_id
    assert menu_by_id[menu_banner_id].parent_id_name == "系统"
    assert menu_by_id[page_banner_create_id].parent_id_name == "展示图管理"
    assert menu_by_id[menu_dashboard_id].parent_id_name == "运营工作台"
    assert all(item.parent_id_name != "ROOT" for item in modules[0].menu)

    portal_modules = await ResourceService(db_session).list_grant_modules(
        module_client=AccountType.PORTAL,
    )
    assert portal_modules == []
