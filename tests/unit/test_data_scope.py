""" Author: Charlie """

import uuid

from sqlalchemy import select

from hei_fastapi_ddd.shared.config.enums import AccountType, DataScope
from hei_fastapi_ddd.shared.security.data_scope import build_data_scope_filter, list_dept_and_child_ids
from hei_fastapi_ddd.shared.security.session import SessionPayload
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.dept_po import SysDept
from hei_fastapi_ddd.contexts.iam.domain.enums import IamRelationType
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_po import SysIamRelation
from tests.iam_relation_helpers import account_dept


async def test_data_scope_defaults_to_self(db_session):
    suffix = uuid.uuid4().hex[:8]
    account_id = f"account_1_{suffix}"
    dept_id = f"dept_1_{suffix}"
    db_session.add_all(
        [
            account_dept(account_id, dept_id),
            account_dept(f"account_2_{suffix}", dept_id),
        ]
    )
    await db_session.commit()

    session = SessionPayload(
        token="token",
        account_id=account_id,
        account_type=AccountType.ADMIN.value,
        permission_keys=["sys:file:page"],
        permission_grants=[],
    )
    condition = await build_data_scope_filter(
        db_session,
        session,
        "sys:file:page",
        owner_column=SysIamRelation.subject_id,
        dept_column=SysIamRelation.target_id,
    )
    rows = (
        (
            await db_session.execute(
                select(SysIamRelation.subject_id).where(
                    SysIamRelation.relation_type == IamRelationType.ACCOUNT_DEPT.value,
                    condition,
                )
            )
        )
        .scalars()
        .all()
    )

    assert rows == [account_id]


async def test_data_scope_all_returns_all_rows(db_session):
    suffix = uuid.uuid4().hex[:8]
    account_ids = [f"account_1_{suffix}", f"account_2_{suffix}"]
    dept_ids = [f"dept_1_{suffix}", f"dept_2_{suffix}"]
    db_session.add_all(
        [
            account_dept(account_ids[0], dept_ids[0]),
            account_dept(account_ids[1], dept_ids[1]),
        ]
    )
    await db_session.commit()

    session = SessionPayload(
        token="token",
        account_id=account_ids[0],
        account_type=AccountType.ADMIN.value,
        permission_keys=["sys:file:page"],
        permission_grants=[
            {
                "permission_key": "sys:file:page",
                "data_scope": DataScope.ALL.value,
                "custom_scope_dept_ids": [],
                "source_type": "ROLE",
                "source_id": "role_1",
            }
        ],
    )
    condition = await build_data_scope_filter(
        db_session,
        session,
        "sys:file:page",
        owner_column=SysIamRelation.subject_id,
        dept_column=SysIamRelation.target_id,
    )
    rows = (
        (
            await db_session.execute(
                select(SysIamRelation.subject_id).where(
                    SysIamRelation.relation_type == IamRelationType.ACCOUNT_DEPT.value,
                    condition,
                )
            )
        )
        .scalars()
        .all()
    )

    assert rows == account_ids


async def test_data_scope_custom_uses_custom_dept_ids(db_session):
    suffix = uuid.uuid4().hex[:8]
    account_ids = [f"account_1_{suffix}", f"account_2_{suffix}"]
    dept_ids = [f"dept_1_{suffix}", f"dept_2_{suffix}"]
    db_session.add_all(
        [
            account_dept(account_ids[0], dept_ids[0]),
            account_dept(account_ids[1], dept_ids[1]),
        ]
    )
    await db_session.commit()

    session = SessionPayload(
        token="token",
        account_id=account_ids[0],
        account_type=AccountType.ADMIN.value,
        permission_keys=["sys:file:page"],
        permission_grants=[
            {
                "permission_key": "sys:file:page",
                "data_scope": DataScope.CUSTOM.value,
                "custom_scope_dept_ids": [dept_ids[1]],
                "source_type": "ACCOUNT",
                "source_id": account_ids[0],
            }
        ],
    )
    condition = await build_data_scope_filter(
        db_session,
        session,
        "sys:file:page",
        owner_column=SysIamRelation.subject_id,
        dept_column=SysIamRelation.target_id,
    )
    rows = (
        (
            await db_session.execute(
                select(SysIamRelation.subject_id).where(
                    SysIamRelation.relation_type == IamRelationType.ACCOUNT_DEPT.value,
                    condition,
                )
            )
        )
        .scalars()
        .all()
    )

    assert rows == [account_ids[1]]


async def test_data_scope_dept_and_child_loads_depts_in_batch(db_session):
    suffix = uuid.uuid4().hex[:8]
    dept_ids = [f"dept_1_{suffix}", f"dept_2_{suffix}", f"dept_3_{suffix}", f"dept_4_{suffix}"]
    account_ids = [f"account_{idx}_{suffix}" for idx in range(1, 5)]
    db_session.add_all(
        [
            SysDept(id=dept_ids[0], name="Dept 1", category="SYS"),
            SysDept(id=dept_ids[1], parent_id=dept_ids[0], name="Dept 2", category="SYS"),
            SysDept(id=dept_ids[2], parent_id=dept_ids[1], name="Dept 3", category="SYS"),
            SysDept(id=dept_ids[3], name="Dept 4", category="SYS"),
            account_dept(account_ids[0], dept_ids[0]),
            account_dept(account_ids[1], dept_ids[1]),
            account_dept(account_ids[2], dept_ids[2]),
            account_dept(account_ids[3], dept_ids[3]),
        ]
    )
    await db_session.commit()

    assert await list_dept_and_child_ids(db_session, [dept_ids[0]]) == dept_ids[:3]

    session = SessionPayload(
        token="token",
        account_id=account_ids[0],
        account_type=AccountType.ADMIN.value,
        dept_ids=[dept_ids[0]],
        permission_keys=["sys:file:page"],
        permission_grants=[
            {
                "permission_key": "sys:file:page",
                "data_scope": DataScope.DEPT_AND_CHILD.value,
                "custom_scope_dept_ids": [],
                "source_type": "GROUP",
                "source_id": "group_1",
            }
        ],
    )
    condition = await build_data_scope_filter(
        db_session,
        session,
        "sys:file:page",
        owner_column=SysIamRelation.subject_id,
        dept_column=SysIamRelation.target_id,
    )
    rows = (
        (
            await db_session.execute(
                select(SysIamRelation.subject_id).where(
                    SysIamRelation.relation_type == IamRelationType.ACCOUNT_DEPT.value,
                    condition,
                )
            )
        )
        .scalars()
        .all()
    )

    assert rows == account_ids[:3]
