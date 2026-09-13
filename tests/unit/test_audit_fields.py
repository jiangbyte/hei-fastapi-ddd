""" Author: Charlie """

from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.dict_po import SysDict
from hei_fastapi_ddd.shared.config.enums import StatusEnum, SysBizCategory
from hei_fastapi_ddd.shared.observability.context import account_id_ctx


async def test_timestamp_mixin_injects_created_and_updated_by(db_session):
    token = account_id_ctx.set("100001")
    try:
        entity = SysDict(
            code="AUDIT_CREATE",
            label="Audit Create",
            value="audit_create",
            category=SysBizCategory.SYS.value,
            status=StatusEnum.ENABLED.value,
        )
        db_session.add(entity)
        await db_session.commit()

        assert entity.created_by == "100001"
        assert entity.updated_by == "100001"
    finally:
        account_id_ctx.reset(token)


async def test_timestamp_mixin_updates_updated_by_only(db_session):
    create_token = account_id_ctx.set("100001")
    try:
        entity = SysDict(
            code="AUDIT_UPDATE",
            label="Audit Update",
            value="audit_update",
            category=SysBizCategory.SYS.value,
            status=StatusEnum.ENABLED.value,
        )
        db_session.add(entity)
        await db_session.commit()
    finally:
        account_id_ctx.reset(create_token)

    update_token = account_id_ctx.set("100002")
    try:
        entity.label = "Audit Updated"
        await db_session.commit()

        assert entity.created_by == "100001"
        assert entity.updated_by == "100002"
    finally:
        account_id_ctx.reset(update_token)


async def test_timestamp_mixin_keeps_audit_empty_without_account_context(db_session):
    token = account_id_ctx.set(None)
    try:
        entity = SysDict(
            code="AUDIT_EMPTY",
            label="Audit Empty",
            value="audit_empty",
            category=SysBizCategory.SYS.value,
            status=StatusEnum.ENABLED.value,
        )
        db_session.add(entity)
        await db_session.commit()

        assert entity.created_by is None
        assert entity.updated_by is None
    finally:
        account_id_ctx.reset(token)
