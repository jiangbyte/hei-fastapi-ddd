""" Author: Charlie

字典聚合根：编码/状态等业务不变量。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from hei_fastapi_ddd.ddd_kernel.domain_exception import DomainException
from hei_fastapi_ddd.ddd_kernel.entity import AggregateRoot

_CODE_PATTERN = re.compile(r"^[A-Z0-9_]+$")
_ALLOWED_STATUS = frozenset({"ENABLED", "DISABLED"})


@dataclass
class DictAggregate(AggregateRoot[str]):
    """系统字典聚合：维护编码格式、状态与基础字段一致性。"""

    id: str
    code: str
    label: str | None = None
    value: str | None = None
    color: str | None = None
    category: str | None = None
    parent_id: str | None = None
    status: str = "ENABLED"
    sort: int = 0

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self, self.id)

    @classmethod
    def create(
        cls,
        *,
        id: str,
        code: str,
        label: str | None = None,
        value: str | None = None,
        color: str | None = None,
        category: str | None = None,
        parent_id: str | None = None,
        status: str = "ENABLED",
        sort: int = 0,
    ) -> DictAggregate:
        """工厂：校验不变量后构造新字典聚合。"""
        # 1. 规范化并校验编码
        normalized = cls._normalize_code(code)
        # 2. 校验状态合法
        status_value = cls._normalize_status(status)
        # 3. 组装聚合实例
        return cls(
            id=id,
            code=normalized,
            label=label,
            value=value,
            color=color,
            category=category,
            parent_id=parent_id,
            status=status_value,
            sort=int(sort or 0),
        )

    def update(
        self,
        *,
        code: str,
        label: str | None,
        value: str | None,
        color: str | None,
        category: str | None,
        parent_id: str | None,
        status: str,
        sort: int,
    ) -> None:
        """更新字典字段并重新校验不变量。"""
        # 1. 禁止自引用为父级
        if parent_id and parent_id == self.id:
            raise DomainException("Dict cannot be its own parent")
        # 2. 写入规范化后的编码与状态
        self.code = self._normalize_code(code)
        self.status = self._normalize_status(status)
        # 3. 更新其余展示/分类字段
        self.label = label
        self.value = value
        self.color = color
        self.category = category
        self.parent_id = parent_id
        self.sort = int(sort or 0)

    def enable(self) -> None:
        """启用字典。"""
        self.status = "ENABLED"

    def disable(self) -> None:
        """停用字典。"""
        self.status = "DISABLED"

    @staticmethod
    def _normalize_code(code: str) -> str:
        """校验并返回字典编码。"""
        # 1. 去空白并要求非空
        value = (code or "").strip()
        if not value:
            raise DomainException("Dict code is required")
        # 2. 限制长度与字符集（大写字母/数字/下划线）
        if len(value) > 50 or not _CODE_PATTERN.fullmatch(value):
            raise DomainException("Dict code must match ^[A-Z0-9_]+$")
        return value

    @staticmethod
    def _normalize_status(status: str) -> str:
        """校验状态枚举。"""
        value = (status or "").strip().upper()
        if value not in _ALLOWED_STATUS:
            raise DomainException(f"Invalid dict status: {status}")
        return value
