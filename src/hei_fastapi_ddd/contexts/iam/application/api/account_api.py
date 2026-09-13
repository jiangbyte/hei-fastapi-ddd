""" Author: Charlie

IAM 对外账户 API 端口：供 auth 等上下文依赖，避免直连基础设施。
"""

from __future__ import annotations

from typing import Any, Protocol


class AccountApi(Protocol):
    """跨上下文账户查询/写入端口。"""

    async def get_account_by_id(self, account_id: str) -> Any | None:
        """按账户 ID 获取账户 PO/视图。"""
        ...

    async def get_account_by_identifier(
        self,
        identifier: str,
        identity_types: list[Any] | None = None,
    ) -> Any | None:
        """按登录标识解析账户。"""
        ...

    async def create_account(self, *args: Any, **kwargs: Any) -> Any:
        """创建账户（注册链路）。"""
        ...

    async def get_required(self, account_id: str) -> Any:
        """按 ID 获取账户，不存在则抛错。"""
        ...
