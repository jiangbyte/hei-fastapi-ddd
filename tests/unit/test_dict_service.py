""" Author: Charlie """


from hei_fastapi_ddd.shared.config.enums import StatusEnum
from hei_fastapi_ddd.contexts.sys.interfaces.http.dict_schemas import (
    DictAdminPageQuery,
    DictCreateRequest,
    DictIdQuery,
    DictIdsRequest,
    DictTreeQuery,
    DictUpdateRequest,
)
from hei_fastapi_ddd.contexts.sys.application.dict.dict_application_service import DictService


def _dict_create_request(**overrides) -> DictCreateRequest:
    data = {
        "code": "GENDER",
        "label": "Gender",
        "value": "gender",
        "color": "#1677ff",
        "category": "BIZ",
        "sort": 10,
        "status": StatusEnum.ENABLED,
    }
    data.update(overrides)
    return DictCreateRequest(**data)


async def _create_dict(db_session, service: DictService, **overrides):
    await service.create(_dict_create_request(**overrides))
    page = await service.page_admin(
        DictAdminPageQuery(
            current=1, size=1, code=overrides.get("code", "GENDER"),
        )
    )
    assert page.records
    item = page.records[0]
    await db_session.rollback()
    return item


async def test_dict_service_create_page_detail_update_delete(db_session):
    service = DictService(db_session)

    created = await _create_dict(db_session, service)
    page = await service.page_admin(
        DictAdminPageQuery(
            current=1, size=20, category="BIZ",
            status=StatusEnum.ENABLED.value,
        )
    )
    detail = await service.get(DictIdQuery(id=created.id))
    await db_session.rollback()
    updated_result = await service.update(
        DictUpdateRequest(
            id=created.id,
            code="GENDER",
            label="Gender Updated",
            value="gender",
            category="BIZ",
            sort=1,
            status=StatusEnum.DISABLED,
        )
    )
    updated = await service.get(DictIdQuery(id=created.id))
    await db_session.rollback()
    deleted_result = await service.delete(DictIdsRequest(ids=[created.id]))

    assert page.total == 1
    assert page.records[0].id == created.id
    assert detail.label == "Gender"
    assert updated_result is None
    assert updated.label == "Gender Updated"
    assert updated.status == StatusEnum.DISABLED
    assert deleted_result is None


async def test_dict_service_delete_is_idempotent_with_missing_ids(db_session):
    """对齐 hei-boot：批量删除对不存在的 ID 静默跳过，不报错。"""
    service = DictService(db_session)
    created = await _create_dict(db_session, service, code="VISIBLE")

    await service.delete(DictIdsRequest(ids=[created.id, "missing"]))
    remaining = await service.page_admin(
        DictAdminPageQuery(current=1, size=20, code="VISIBLE")
    )
    assert remaining.total == 0


async def test_dict_service_tree_supports_category_filter_and_orphan_roots(db_session):
    service = DictService(db_session)
    profile_root = await _create_dict(
        db_session,
        service,
        code="PROFILE_GENDER",
        label="Gender",
        sort=1,
    )
    await service.create(
        _dict_create_request(
            code="PROFILE_GENDER_MALE",
            label="Male",
            value="M",
            parent_id=profile_root.id,
            sort=2,
        )
    )
    await service.create(
        _dict_create_request(
            code="ORDER_STATUS",
            label="Order Status",
            category="SYS",
            sort=3,
        )
    )
    await service.create(
        _dict_create_request(
            code="PROFILE_ORPHAN",
            label="Orphan",
            parent_id="missing-parent",
            sort=4,
        )
    )

    profile_tree = await service.list_tree(DictTreeQuery(category="BIZ"))
    all_tree = await service.list_tree(DictTreeQuery())

    assert [node.code for node in profile_tree] == ["PROFILE_GENDER", "PROFILE_ORPHAN"]
    assert profile_tree[0].children[0].code == "PROFILE_GENDER_MALE"
    assert [node.code for node in all_tree] == [
        "PROFILE_GENDER",
        "ORDER_STATUS",
        "PROFILE_ORPHAN",
    ]


async def test_dict_service_fills_parent_id_name_in_batch(db_session):
    service = DictService(db_session)
    label_parent = await _create_dict(
        db_session,
        service,
        code="PARENT_LABEL",
        label="Parent Label",
        sort=1,
    )
    label_child = await _create_dict(
        db_session,
        service,
        code="PARENT_LABEL_CHILD",
        label="Label Child",
        parent_id=label_parent.id,
        sort=2,
    )
    code_parent = await _create_dict(db_session, service, code="PARENT_CODE", label=None, sort=3)
    code_child = await _create_dict(
        db_session,
        service,
        code="PARENT_CODE_CHILD",
        label="Code Child",
        parent_id=code_parent.id,
        sort=4,
    )

    page = await service.page_admin(
        DictAdminPageQuery(
            current=1, size=20, category="BIZ",
            status=StatusEnum.ENABLED.value,
        )
    )
    detail = await service.get(DictIdQuery(id=label_child.id))
    tree = await service.list_tree(DictTreeQuery(category="BIZ"))

    page_records = {item.id: item for item in page.records}
    assert page_records[label_parent.id].parent_id_name is None
    assert page_records[label_child.id].parent_id_name == "Parent Label"
    assert page_records[code_child.id].parent_id_name == "PARENT_CODE"
    assert detail.parent_id_name == "Parent Label"
    assert tree[0].children[0].parent_id_name == "Parent Label"


async def test_dict_service_parent_filter_matches_direct_children_only(db_session):
    service = DictService(db_session)
    parent = await _create_dict(
        db_session,
        service,
        code="COMMON_STATUS",
        label="Common Status",
        sort=1,
    )
    enabled = await _create_dict(
        db_session,
        service,
        code="COMMON_STATUS_ENABLED",
        label="Enabled",
        parent_id=parent.id,
        sort=2,
    )
    disabled = await _create_dict(
        db_session,
        service,
        code="COMMON_STATUS_DISABLED",
        label="Disabled",
        parent_id=parent.id,
        sort=3,
    )
    await service.create(
        _dict_create_request(
            code="COMMON_STATUS_ENABLED_CHILD",
            label="Enabled Child",
            parent_id=enabled.id,
            sort=4,
        )
    )

    page = await service.page_admin(
        DictAdminPageQuery(
            current=1, size=20, category="BIZ",
            parent_id=parent.id,
        )
    )

    # 对齐 hei-boot：parent_id 仅精确匹配直接子节点（不含父节点自身）。
    assert page.total == 2
    assert {item.id for item in page.records} == {enabled.id, disabled.id}
