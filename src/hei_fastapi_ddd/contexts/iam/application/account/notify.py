""" Author: Charlie

账号注销生命周期通知（软注销确认 / 保留期到期彻底删除）。
"""

from __future__ import annotations

import logging
from typing import Any

from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.email.sender import is_mail_configured, send_templated_mail
from hei_fastapi_ddd.shared.sms.sender import send_templated_sms

logger = logging.getLogger(__name__)


async def notify_account_cancel_lifecycle(
    *,
    scene: str,
    email: str | None,
    phone: str | None,
    variables: dict[str, Any],
) -> None:
    """尽力发送邮件/短信；未配置通道时静默跳过，失败不阻断主流程。"""
    to_email = (email or "").strip()
    to_phone = (phone or "").strip()
    if to_email and is_mail_configured():
        try:
            await send_templated_mail(scene, to_email, variables)
        except Exception:
            logger.warning(
                "Account cancel mail notify failed",
                extra={"scene": scene, "email": to_email},
                exc_info=True,
            )
    if to_phone:
        tmpl = config_reader.get_sms_template(scene)
        code = (tmpl.get("code") or "").strip()
        if code:
            try:
                await send_templated_sms(scene, to_phone, variables)
            except Exception:
                logger.warning(
                    "Account cancel SMS notify failed",
                    extra={"scene": scene, "phone": to_phone},
                    exc_info=True,
                )
