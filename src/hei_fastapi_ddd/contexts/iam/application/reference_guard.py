""" Author: Charlie

引用守卫：统计实体的被引用数量，并在删除/调整层级前阻断存在引用或非法层级关系的操作。
"""

from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.shared.exceptions.business import ConflictError
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.dept_po import SysDept
from hei_fastapi_ddd.contexts.iam.domain.enums import (
    GrantSubjectType,
    IamRelationSubjectType,
    IamRelationTargetType,
    IamRelationType,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_po import SysIamRelation
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.resource_po import SysResource
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.role_po import SysRole


def unique_ids(values: Iterable[str]) -> list[str]:
    """按原始顺序去重并保留非重复的 ID 列表。"""
    return list(dict.fromkeys(values))


def raise_if_referenced(entity_name: str, counts: dict[str, int]) -> None:
    """当存在引用计数大于 0 时抛出冲突错误，附带各引用来源明细。"""
    references = {key: value for key, value in counts.items() if value > 0}
    if not references:
        return
    details = ", ".join(f"{key}={value}" for key, value in sorted(references.items()))
    raise ConflictError(f"{entity_name} is referenced: {details}")


async def count_role_references(db: AsyncSession, role_ids: list[str]) -> dict[str, int]:
    """统计角色被账户、组及资源授权引用的数量。"""
    ids = unique_ids(role_ids)
    if not ids:
        return {}
    return {
        "account_roles": await _count_relation_targets(
            db, IamRelationType.ACCOUNT_ROLE, IamRelationTargetType.ROLE.value, ids
        ),
        "group_roles": await _count_relation_targets(
            db, IamRelationType.GROUP_ROLE, IamRelationTargetType.ROLE.value, ids
        ),
        "resource_grants": await _count(
            db,
            select(func.count())
            .select_from(SysIamRelation)
            .where(
                SysIamRelation.subject_type == GrantSubjectType.ROLE.value,
                SysIamRelation.subject_id.in_(ids),
                SysIamRelation.relation_type == IamRelationType.SUBJECT_RESOURCE_GRANT.value,
            ),
        ),
    }


async def count_group_references(db: AsyncSession, group_ids: list[str]) -> dict[str, int]:
    """统计账户组被账户、角色及资源授权引用的数量。"""
    ids = unique_ids(group_ids)
    if not ids:
        return {}
    return {
        "account_groups": await _count_relation_targets(
            db, IamRelationType.ACCOUNT_GROUP, IamRelationTargetType.GROUP.value, ids
        ),
        "group_roles": await _count(
            db,
            select(func.count())
            .select_from(SysIamRelation)
            .where(
                SysIamRelation.subject_type == IamRelationSubjectType.GROUP.value,
                SysIamRelation.subject_id.in_(ids),
                SysIamRelation.relation_type == IamRelationType.GROUP_ROLE.value,
            ),
        ),
        "resource_grants": await _count(
            db,
            select(func.count())
            .select_from(SysIamRelation)
            .where(
                SysIamRelation.subject_type == GrantSubjectType.GROUP.value,
                SysIamRelation.subject_id.in_(ids),
                SysIamRelation.relation_type == IamRelationType.SUBJECT_RESOURCE_GRANT.value,
            ),
        ),
    }


async def count_dept_references(db: AsyncSession, dept_ids: list[str]) -> dict[str, int]:
    """统计部门被子部门、账户、角色及资源权限作用域引用的数量。"""
    ids = unique_ids(dept_ids)
    if not ids:
        return {}
    return {
        "child_depts": await _count(
            db, select(func.count()).select_from(SysDept).where(SysDept.parent_id.in_(ids))
        ),
        "account_depts": await _count_relation_targets(
            db, IamRelationType.ACCOUNT_DEPT, IamRelationTargetType.DEPT.value, ids
        ),
        "owner_roles": await _count(
            db, select(func.count()).select_from(SysRole).where(SysRole.owner_dept_id.in_(ids))
        ),
        "resource_permission_scopes": await _count_resource_permission_scope_refs(db, ids),
    }


async def count_resource_references(db: AsyncSession, resource_ids: list[str]) -> dict[str, int]:
    """统计资源被子资源、权限及授权关系引用的数量。"""
    ids = unique_ids(resource_ids)
    if not ids:
        return {}
    return {
        "child_resources": await _count(
            db, select(func.count()).select_from(SysResource).where(SysResource.parent_id.in_(ids))
        ),
        "resource_permissions": await _count(
            db,
            select(func.count())
            .select_from(SysIamRelation)
            .where(
                SysIamRelation.subject_type == IamRelationSubjectType.RESOURCE.value,
                SysIamRelation.subject_id.in_(ids),
                SysIamRelation.relation_type == IamRelationType.RESOURCE_PERMISSION.value,
            ),
        ),
        "resource_grants": await _count_relation_targets(
            db, IamRelationType.SUBJECT_RESOURCE_GRANT, IamRelationTargetType.RESOURCE.value, ids
        ),
    }


async def ensure_parent_exists(
    db: AsyncSession, model, parent_id: str | None, entity_name: str
) -> None:
    """校验父级实体存在，不存在则抛出冲突错误。"""
    if not parent_id:
        return
    if not await db.get(model, parent_id):
        raise ConflictError(f"{entity_name} parent does not exist")


async def ensure_not_self_or_descendant(
    db: AsyncSession,
    model,
    entity_id: str,
    parent_id: str | None,
    entity_name: str,
) -> None:
    """校验父级既不是自身也不是自身后代，防止形成环或自引用。"""
    if not parent_id:
        return
    if parent_id == entity_id:
        raise ConflictError(f"{entity_name} cannot move under itself")
    descendants = await list_descendant_ids(db, model, entity_id)
    if parent_id in descendants:
        raise ConflictError(f"{entity_name} cannot move under its descendant")


async def list_descendant_ids(db: AsyncSession, model, entity_id: str) -> set[str]:
    """从全表父子关系构建邻接表，广度优先收集实体全部后代 ID。"""
    return (await list_descendant_ids_many(db, model, [entity_id])).get(entity_id, set())


async def list_descendant_ids_many(
    db: AsyncSession,
    model,
    entity_ids: Iterable[str],
) -> dict[str, set[str]]:
    """一次加载父子关系，批量计算多个实体的全部后代 ID 集合。

    替代逐实体全表加载（原实现每调用一次就 SELECT 全表一次），
    多目标删除/校验场景下将 N 次全表扫描降为 1 次。
    """
    root_ids = unique_ids(entity_ids)
    if not root_ids:
        return {}
    rows = (await db.execute(select(model.id, model.parent_id))).all()
    children_by_parent: dict[str, list[str]] = {}
    for current_id, parent_id in rows:
        if parent_id:
            children_by_parent.setdefault(str(parent_id), []).append(str(current_id))

    result: dict[str, set[str]] = {}
    for root_id in root_ids:
        descendants: set[str] = set()
        stack = list(children_by_parent.get(root_id, []))
        while stack:
            current_id = stack.pop()
            if current_id in descendants:
                continue
            descendants.add(current_id)
            stack.extend(children_by_parent.get(current_id, []))
        result[root_id] = descendants
    return result


async def _count(db: AsyncSession, stmt) -> int:
    """执行 count 语句并返回标量结果。"""
    return int((await db.execute(stmt)).scalar_one())


async def _count_relation_targets(
    db: AsyncSession,
    relation_type: IamRelationType,
    target_type: str,
    target_ids: list[str],
) -> int:
    """统计指定关系类型下目标类型命中目标 ID 列表的关系数量。"""
    return await _count(
        db,
        select(func.count())
        .select_from(SysIamRelation)
        .where(
            SysIamRelation.relation_type == relation_type.value,
            SysIamRelation.target_type == target_type,
            SysIamRelation.target_id.in_(target_ids),
        ),
    )


async def _count_resource_permission_scope_refs(db: AsyncSession, dept_ids: list[str]) -> int:
    """统计资源权限的 custom_scope_dept_ids 中引用了目标部门的关系数量。"""
    rows = (
        (
            await db.execute(
                select(SysIamRelation.custom_scope_dept_ids).where(
                    SysIamRelation.relation_type == IamRelationType.RESOURCE_PERMISSION.value,
                    SysIamRelation.custom_scope_dept_ids.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )
    return _count_scope_refs(rows, dept_ids)


def _count_scope_refs(rows, dept_ids: list[str]) -> int:
    """统计自定义作用域列表中与目标部门集合存在交集的行数。"""
    target_ids = set(dept_ids)
    count = 0
    for row in rows:
        values = row or []
        if target_ids.intersection(str(value) for value in values):
            count += 1
    return count
