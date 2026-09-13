"""领域异常基类。"""

from __future__ import annotations


class DomainException(Exception):
    """领域规则违反时抛出，携带可读消息与业务错误码。"""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or "DOMAIN_ERROR"
