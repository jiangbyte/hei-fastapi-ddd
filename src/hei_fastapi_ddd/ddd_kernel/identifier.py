"""强类型标识包装。"""

from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class Identifier(Generic[T]):
    """标识值包装：避免原始类型在领域层到处传递。"""

    __slots__ = ("_value",)

    def __init__(self, value: T) -> None:
        self._value = value

    @property
    def value(self) -> T:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Identifier):
            return NotImplemented
        return type(self) is type(other) and self._value == other._value

    def __hash__(self) -> int:
        return hash((type(self), self._value))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value!r})"
