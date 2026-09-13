"""值对象基类。"""

from __future__ import annotations


class ValueObject:
    """值对象：按属性值判定相等，无独立标识。"""

    def __eq__(self, other: object) -> bool:
        # 1. 类型不一致则不等
        if other is None or type(self) is not type(other):
            return NotImplemented
        # 2. 优先按 __slots__ 比较（若定义）
        slots = getattr(self, "__slots__", None)
        if slots is not None:
            for name in slots:
                if getattr(self, name) != getattr(other, name):
                    return False
            return True
        # 3. 否则按 __dict__ 比较全部状态
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        slots = getattr(self, "__slots__", None)
        if slots is not None:
            return hash(tuple(getattr(self, name) for name in slots))
        return hash(tuple(sorted(self.__dict__.items())))
