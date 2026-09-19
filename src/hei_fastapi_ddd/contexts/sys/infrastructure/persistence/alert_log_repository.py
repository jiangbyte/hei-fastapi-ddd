"""告警日志仓储。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_alert_po import SysAlertLog
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id


class AlertLogRepositoryImpl:
    """告警冷却与落库。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def latest_created_by_rules(self, rule_names: list[str]) -> dict[str, datetime]:
        if not rule_names:
            return {}
        rows = (
            await self.db.execute(
                select(SysAlertLog.rule_name, func.max(SysAlertLog.created_at))
                .where(SysAlertLog.rule_name.in_(rule_names))
                .group_by(SysAlertLog.rule_name)
            )
        ).all()
        return {str(rule): created_at for rule, created_at in rows}

    async def append_many(self, items: list[Mapping[str, Any]]) -> None:
        for item in items:
            self.db.add(
                SysAlertLog(
                    id=generate_snowflake_id(),
                    rule_name=item["rule_name"],
                    severity=item["severity"],
                    summary=item["summary"],
                    details=item.get("details"),
                    notified_via=item.get("notified_via"),
                )
            )
        await self.db.flush()
