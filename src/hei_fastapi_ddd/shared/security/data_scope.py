""" Author: Charlie

数据权限：根据会话中的权限授权计算数据范围，并生成 SQLAlchemy 过滤条件。

数据范围枚举为 ALL / DEPT_AND_CHILD / DEPT / SELF / CUSTOM，
由 find_permission_grant 定位授权后转换为布尔表达式。
"""

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import false, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from hei_fastapi_ddd.shared.config.enums import DataScope
from hei_fastapi_ddd.shared.security.session import PermissionGrantPayload, SessionPayload

# 写操作数据范围断言统一使用 :page 权限键（对齐 hei-boot DataScopeResolver）。
IAM_ACCOUNT_PAGE = "iam:account:page"
IAM_ROLE_PAGE = "iam:role:page"
IAM_GROUP_PAGE = "iam:group:page"
IAM_POSITION_PAGE = "iam:position:page"
IAM_DEPT_PAGE = "iam:dept:page"


@dataclass(frozen=True, slots=True)
class DataScopeColumns:
    """数据范围过滤所依赖的列：负责人列与部门列。"""

    owner: ColumnElement[bool] | None = None
    dept: ColumnElement[bool] | None = None


def find_permission_grant(
    session: SessionPayload,
    permission_key: str,
) -> PermissionGrantPayload | None:
    """在会话授权列表中定位指定权限码的授权（取最后一条）。"""
    for grant in reversed(session.permission_grants):
        if grant["permission_key"] == permission_key:
            return grant
    return None


def has_unrestricted_data_scope(session: SessionPayload, permission_key: str) -> bool:
    """判断是否持有超级权限（*:*:*）或 ALL 数据范围。"""
    if "*:*:*" in session.permission_keys:
        return True
    grant = find_permission_grant(session, permission_key)
    return bool(grant and DataScope(str(grant["data_scope"])) == DataScope.ALL)


def default_owner_dept_id(session: SessionPayload | None) -> str | None:
    """客户端未提供 owner_dept_id 时，为新行选取默认部门。"""
    if session is None or not session.dept_ids:
        return None
    return session.dept_ids[0]


async def resolve_data_scope_dept_ids(
    db: AsyncSession,
    session: SessionPayload,
    permission_key: str,
) -> list[str] | None:
    """将数据范围解析为可见部门 ID 列表；None 表示不限制。"""
    if has_unrestricted_data_scope(session, permission_key):
        return None

    grant = find_permission_grant(session, permission_key)
    data_scope = DataScope(str(grant["data_scope"])) if grant else DataScope.SELF
    custom_scope_dept_ids = list(grant["custom_scope_dept_ids"]) if grant else []

    if data_scope == DataScope.ALL:
        return None
    if data_scope == DataScope.DEPT:
        return _unique_ids(session.dept_ids)
    if data_scope == DataScope.DEPT_AND_CHILD:
        return await list_dept_and_child_ids(db, session.dept_ids)
    if data_scope == DataScope.CUSTOM:
        return _unique_ids(custom_scope_dept_ids)
    return []


async def build_data_scope_filter(
    db: AsyncSession,
    session: SessionPayload,
    permission_key: str,
    *,
    owner_column=None,
    dept_column=None,
) -> ColumnElement[bool]:
    """按数据范围构造 SQLAlchemy 过滤条件，供仓储层查询复用。"""
    if has_unrestricted_data_scope(session, permission_key):
        return true()

    grant = find_permission_grant(session, permission_key)
    data_scope = DataScope(str(grant["data_scope"])) if grant else DataScope.SELF

    if data_scope == DataScope.SELF:
        return owner_column == session.account_id if owner_column is not None else false()

    dept_ids = await resolve_data_scope_dept_ids(db, session, permission_key)
    if dept_column is not None:
        return _in_or_false(dept_column, dept_ids or [])
    # 尚无 owner_dept_id 列：DEPT/CUSTOM 范围降级为通过 created_by 的 SELF。
    if owner_column is not None and data_scope in {
        DataScope.DEPT,
        DataScope.DEPT_AND_CHILD,
        DataScope.CUSTOM,
    }:
        return owner_column == session.account_id
    return _in_or_false(dept_column, dept_ids or [])


async def list_dept_and_child_ids(db: AsyncSession, dept_ids: Iterable[str]) -> list[str]:
    """展开部门及所有子部门 ID（延迟导入避免 core→module 循环依赖）。"""
    from hei_fastapi_ddd.contexts.iam.infrastructure.dept_resolver import resolver as dept_resolver

    return await dept_resolver.list_dept_and_child_ids(db, dept_ids)


def _in_or_false(column, values: Iterable[str]) -> ColumnElement[bool]:
    """构造 IN 过滤；列缺失或值列表为空时返回恒假。"""
    unique_values = _unique_ids(values)
    if column is None or not unique_values:
        return false()
    return column.in_(unique_values)


def _unique_ids(values: Iterable[str]) -> list[str]:
    """去重、去空并按字典序排序的 ID 列表。"""
    return sorted({str(value) for value in values if value})
