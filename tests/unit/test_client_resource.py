""" Author: Charlie """

import uuid

from hei_fastapi_ddd.contexts.iam.application.client.client_application_service import (
    ClientModuleService,
    ClientResourceService,
)
from hei_fastapi_ddd.contexts.iam.domain.enums import GrantSubjectType, ResourceType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.client_po import (
    SysClientModule,
    SysClientResource,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_repository import (
    IamRelationRepository,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po import SysRole
from hei_fastapi_ddd.contexts.iam.interfaces.http.client_schemas import ClientModuleSelectorQuery
from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum


async def test_client_module_selector_filters_by_account_type(db_session):
    db_session.add_all(
        [
            SysClientModule(
                id="m_admin",
                name="A",
                code="a",
                account_type=AccountType.ADMIN.value,
            ),
            SysClientModule(
                id="m_portal",
                name="P",
                code="p",
                account_type=AccountType.PORTAL.value,
            ),
        ]
    )
    await db_session.commit()

    options = await ClientModuleService(db_session).selector(
        ClientModuleSelectorQuery(account_type=AccountType.PORTAL)
    )
    assert [item.id for item in options] == ["m_portal"]


async def test_client_resource_grant_isolated_from_resource_ids(db_session):
    db_session.add_all(
        [
            SysClientModule(
                id="m1",
                name="Default",
                code="default",
                account_type=AccountType.ADMIN.value,
            ),
            SysClientResource(
                id="cr1",
                code="home",
                name="Home",
                resource_type=ResourceType.MENU.value,
                module_id="m1",
            ),
            SysRole(id="role1", code="demo", name="Demo", status=StatusEnum.ENABLED.value),
        ]
    )
    await db_session.commit()

    class GrantItem:
        def __init__(self, resource_id: str, permission_keys: list[str] | None = None):
            self.resource_id = resource_id
            self.permission_keys = permission_keys or []

    relations = IamRelationRepository(db_session)
    await relations.replace_subject_client_resource_grant_infos(
        GrantSubjectType.ROLE,
        "role1",
        [GrantItem("cr1")],
        account_type=AccountType.ADMIN,
    )
    await db_session.commit()

    grants = await relations.list_subject_client_resource_grants(
        GrantSubjectType.ROLE,
        "role1",
        account_type=AccountType.ADMIN,
    )
    assert [item["resource_id"] for item in grants] == ["cr1"]

    modules = await ClientResourceService(db_session).list_grant_modules(AccountType.ADMIN)
    assert len(modules) == 1
    assert modules[0].menu[0].id == "cr1"

    portal_modules = await ClientResourceService(db_session).list_grant_modules(
        AccountType.PORTAL
    )
    assert portal_modules == []


async def test_client_resource_tree_filters_by_account_type(db_session):
    suffix = uuid.uuid4().hex[:8]
    admin_module_id = f"m_admin_{suffix}"
    portal_module_id = f"m_portal_{suffix}"
    db_session.add_all(
        [
            SysClientModule(
                id=admin_module_id,
                name="Admin Mod",
                code=f"admin-default-{suffix}",
                account_type=AccountType.ADMIN.value,
            ),
            SysClientModule(
                id=portal_module_id,
                name="Portal Mod",
                code=f"portal-default-{suffix}",
                account_type=AccountType.PORTAL.value,
            ),
            SysClientResource(
                id=f"cr_admin_{suffix}",
                code="home",
                name="Admin Home",
                resource_type=ResourceType.MENU.value,
                module_id=admin_module_id,
            ),
            SysClientResource(
                id=f"cr_portal_{suffix}",
                code="home",
                name="Portal Home",
                resource_type=ResourceType.MENU.value,
                module_id=portal_module_id,
            ),
        ]
    )
    await db_session.commit()

    from hei_fastapi_ddd.contexts.iam.interfaces.http.client_schemas import ClientResourceTreeQuery

    tree = await ClientResourceService(db_session).list_tree(
        None,
        ClientResourceTreeQuery(account_type=AccountType.PORTAL),
    )
    assert [node.id for node in tree] == [f"cr_portal_{suffix}"]
