"""Author: Charlie

资料写入端口：供 IAM 等上下文在开户时同步 profile，避免直连 profile 基础设施。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class ProfileUpsertPort(Protocol):
    """跨上下文资料 upsert 端口。"""

    async def upsert_admin_profile(self, data: Mapping[str, Any]) -> None:
        """创建或更新管理端资料。"""
        ...

    async def upsert_portal_profile(self, data: Mapping[str, Any]) -> None:
        """创建或更新门户端资料。"""
        ...
