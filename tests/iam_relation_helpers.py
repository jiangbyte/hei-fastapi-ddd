""" Author: Charlie """

from hei_fastapi_ddd.contexts.iam.domain.enums import (
    GrantMode,
    GrantSubjectType,
    IamRelationSubjectType,
    IamRelationTargetType,
    IamRelationType,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.relation_po import SysIamRelation
from hei_fastapi_ddd.shared.config.enums import AccountType, DataScope


def account_role(
    account_id: str,
    role_id: str,
    *,
    account_type: str = AccountType.ADMIN.value,
    **kwargs,
) -> SysIamRelation:
    return SysIamRelation(
        subject_type=IamRelationSubjectType.ACCOUNT.value,
        subject_id=account_id,
        account_type=account_type,
        relation_type=IamRelationType.ACCOUNT_ROLE.value,
        target_type=IamRelationTargetType.ROLE.value,
        target_id=role_id,
        **kwargs,
    )


def account_group(
    account_id: str,
    group_id: str,
    *,
    account_type: str = AccountType.ADMIN.value,
    **kwargs,
) -> SysIamRelation:
    return SysIamRelation(
        subject_type=IamRelationSubjectType.ACCOUNT.value,
        subject_id=account_id,
        account_type=account_type,
        relation_type=IamRelationType.ACCOUNT_GROUP.value,
        target_type=IamRelationTargetType.GROUP.value,
        target_id=group_id,
        **kwargs,
    )


def account_dept(
    account_id: str,
    dept_id: str,
    *,
    account_type: str = AccountType.ADMIN.value,
    **kwargs,
) -> SysIamRelation:
    return SysIamRelation(
        subject_type=IamRelationSubjectType.ACCOUNT.value,
        subject_id=account_id,
        account_type=account_type,
        relation_type=IamRelationType.ACCOUNT_DEPT.value,
        target_type=IamRelationTargetType.DEPT.value,
        target_id=dept_id,
        **kwargs,
    )


def group_role(
    group_id: str,
    role_id: str,
    *,
    account_type: str = AccountType.ADMIN.value,
    **kwargs,
) -> SysIamRelation:
    return SysIamRelation(
        subject_type=IamRelationSubjectType.GROUP.value,
        subject_id=group_id,
        account_type=account_type,
        relation_type=IamRelationType.GROUP_ROLE.value,
        target_type=IamRelationTargetType.ROLE.value,
        target_id=role_id,
        **kwargs,
    )


def resource_permission(
    resource_id: str,
    permission_key: str,
    *,
    account_type: str = AccountType.ADMIN.value,
    data_scope: DataScope | str = DataScope.SELF,
    custom_scope_dept_ids: list[str] | None = None,
    **kwargs,
) -> SysIamRelation:
    return SysIamRelation(
        subject_type=IamRelationSubjectType.RESOURCE.value,
        subject_id=resource_id,
        account_type=account_type,
        relation_type=IamRelationType.RESOURCE_PERMISSION.value,
        target_type=IamRelationTargetType.PERMISSION.value,
        target_key=permission_key,
        data_scope=data_scope.value if isinstance(data_scope, DataScope) else data_scope,
        custom_scope_dept_ids=list(custom_scope_dept_ids or []),
        **kwargs,
    )


def subject_resource_grant(
    subject_type: GrantSubjectType,
    subject_id: str,
    resource_id: str,
    *,
    account_type: str = AccountType.ADMIN.value,
    grant_mode: GrantMode | str = GrantMode.CASCADE,
    **kwargs,
) -> SysIamRelation:
    return SysIamRelation(
        subject_type=subject_type.value,
        subject_id=subject_id,
        account_type=account_type,
        relation_type=IamRelationType.SUBJECT_RESOURCE_GRANT.value,
        target_type=IamRelationTargetType.RESOURCE.value,
        target_id=resource_id,
        grant_mode=grant_mode.value if isinstance(grant_mode, GrantMode) else grant_mode,
        **kwargs,
    )
