"""Author: Charlie

绑定验证码端口：供 profile 等上下文消费，避免依赖 auth 基础设施。
"""

from __future__ import annotations

from typing import Protocol

from hei_fastapi_ddd.shared.config.enums import AccountType


class AuthBindCodePort(Protocol):
    """邮箱/手机绑定验证码发送与校验。"""

    async def send_bind_code(
        self,
        *,
        account_type: AccountType,
        channel: str,
        target: str,
        account_id: str,
    ) -> None:
        ...

    async def consume_bind_code(
        self,
        *,
        account_type: AccountType,
        channel: str,
        account_id: str,
        target: str,
        code: str | None,
    ) -> None:
        ...
