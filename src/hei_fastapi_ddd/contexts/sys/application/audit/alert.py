""" Author: Charlie

告警分发器 — 通过邮件 / 消息推送 / 自定义 Webhook 发送告警，含冷却。
"""
import json
import logging
from datetime import UTC, datetime, timedelta

from hei_fastapi_ddd.contexts.sys.application.audit.analyzer import AlertEvent
from hei_fastapi_ddd.contexts.sys.domain.audit.repository import AlertLogRepository
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.email.sender import send_mail
from hei_fastapi_ddd.shared.security.safe_url import UnsafeUrlError, validate_outbound_url
from hei_fastapi_ddd.shared.security.signature import sign_feishu

logger = logging.getLogger(__name__)


class AlertDispatcher:
    """告警分发器，带冷却去重。"""

    async def dispatch(self, alert_repo: AlertLogRepository, events: list[AlertEvent]) -> None:
        """过滤 + 去重 + 发送 + 记录。"""
        if not events:
            return

        default_cooldown = max(60, settings.audit_alert.alert_cooldown_seconds)
        rule_names = list(dict.fromkeys(event.rule_name for event in events))
        latest_by_rule = await alert_repo.latest_created_by_rules(rule_names)
        now = datetime.now(UTC)
        new_events: list[AlertEvent] = []
        for event in events:
            cooldown_sec = (
                event.cooldown_seconds
                if event.cooldown_seconds is not None
                else default_cooldown
            )
            cooldown_sec = max(60, int(cooldown_sec))
            latest = latest_by_rule.get(event.rule_name)
            if latest is not None:
                if latest.tzinfo is None:
                    latest = latest.replace(tzinfo=UTC)
                if latest >= now - timedelta(seconds=cooldown_sec):
                    logger.info(
                        "Audit alert suppressed: rule=%s cooldown=%ss",
                        event.rule_name,
                        cooldown_sec,
                    )
                    continue
            new_events.append(event)

        if not new_events:
            return

        for event in new_events:
            await self._send_alert(event)

        await alert_repo.append_many(
            [
                {
                    "rule_name": event.rule_name,
                    "severity": event.severity,
                    "summary": event.summary,
                    "details": event.details,
                    "notified_via": self._notify_method(),
                }
                for event in new_events
            ]
        )

    def _notify_method(self) -> str:
        """汇总当前启用的通知渠道，用于记录到告警历史。"""
        cfg = settings.audit_alert
        parts = []
        if (
            cfg.notify_email
            and settings.mail.host
            and settings.mail.from_email
            and (config_reader.get("AUDIT_ALERT_NOTIFY_EMAIL_TO") or "").strip()
        ):
            parts.append("email")
        if cfg.notify_push:
            parts.append("push")
        if cfg.notify_custom_webhook and cfg.webhook_url:
            parts.append("webhook")
        return ",".join(parts) if parts else "none"

    async def _send_alert(self, event: AlertEvent) -> None:
        """发送单条告警（邮件 / 推送 / 自定义 Webhook）。"""
        await self._send_email(event)
        await self._send_push(event)
        await self._send_webhook(event)

    async def _send_email(self, event: AlertEvent) -> None:
        """邮件发送（静默失败不阻塞流程），收件人取 AUDIT_ALERT_NOTIFY_EMAIL_TO。"""
        if not settings.audit_alert.notify_email:
            return
        if not settings.mail.host or not settings.mail.from_email:
            return
        to_email = (config_reader.get("AUDIT_ALERT_NOTIFY_EMAIL_TO") or "").strip()
        if not to_email:
            # 未配置告警收件人则跳过，避免发给发件人自身。
            return
        try:
            subject = f"[{event.severity}] 审计告警: {event.summary}"
            body = (
                f"规则: {event.rule_name}\n"
                f"级别: {event.severity}\n"
                f"摘要: {event.summary}\n"
                f"时间: {datetime.now(UTC).isoformat()}"
            )
            if event.details:
                body += f"\n详情: {json.dumps(event.details, ensure_ascii=False)}"
            await send_mail(to_email, subject, body)
        except Exception:
            logger.exception("Failed to send alert email for %s", event.rule_name)

    async def _send_push(self, event: AlertEvent) -> None:
        """复用消息推送配置（钉钉 / 飞书 / 企微）。"""
        if not settings.audit_alert.notify_push:
            return
        try:
            from hei_fastapi_ddd.shared.push.sender import send_push

            title = f"[{event.severity}] 审计告警"
            content = f"{event.summary}\n规则: {event.rule_name}"
            await send_push(title, content)
        except Exception:
            logger.exception("Failed to send alert push for %s", event.rule_name)

    async def _send_webhook(self, event: AlertEvent) -> None:
        """自定义 Webhook 发送（静默失败不阻塞流程）。"""
        if not settings.audit_alert.notify_custom_webhook:
            return
        url = settings.audit_alert.webhook_url
        secret = settings.audit_alert.webhook_secret
        if not url:
            return

        payload = {
            "msg_type": "text",
            "content": {"text": (f"[{event.severity}] {event.summary}\n规则: {event.rule_name}")},
        }

        if secret:
            timestamp, sign = sign_feishu(secret)
            payload["timestamp"] = timestamp
            payload["sign"] = sign

        try:
            validate_outbound_url(url)
            import httpx

            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                await client.post(url, json=payload)
        except UnsafeUrlError:
            logger.warning("Blocked unsafe alert webhook url for %s", event.rule_name)
        except Exception:
            logger.exception("Failed to send alert webhook for %s", event.rule_name)


async def send_test_webhook(webhook_url: str, webhook_secret: str = "") -> str:
    """发送测试 Webhook 消息。成功返回空字符串，失败返回错误信息。"""
    if not webhook_url:
        return "Webhook URL 为空"

    try:
        url = validate_outbound_url(webhook_url)
        payload = {
            "msg_type": "text",
            "content": {
                "text": "HEI-FastAPI 审计告警系统测试消息\n\n如果收到此消息，说明 Webhook 配置正确。"
            },
        }

        if webhook_secret:
            ts, sign = sign_feishu(webhook_secret)
            payload["timestamp"] = ts
            payload["sign"] = sign

        import httpx

        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                return f"HTTP {resp.status_code}: {resp.text[:200]}"
        return ""
    except UnsafeUrlError as exc:
        return f"Webhook URL 不安全: {exc}"
    except Exception as exc:
        return f"发送失败: {exc}"


async def send_test_push() -> str:
    """通过默认消息推送引擎发送测试消息。成功返回空串。"""
    try:
        from hei_fastapi_ddd.shared.push.sender import send_push

        await send_push(
            "审计告警测试",
            "HEI-FastAPI 审计告警系统测试消息\n\n如果收到此消息，说明消息推送配置可复用于审计告警。",
        )
        return ""
    except Exception as exc:
        return f"推送失败: {exc}"


alert_dispatcher = AlertDispatcher()
