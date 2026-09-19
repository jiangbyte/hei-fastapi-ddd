""" Author: Charlie

消息推送适配器 — 钉钉 / 飞书 / 企业微信机器人 Webhook。
"""
from __future__ import annotations

import logging

from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.http.client import get_http_client
from hei_fastapi_ddd.shared.security.safe_url import UnsafeUrlError, validate_outbound_url
from hei_fastapi_ddd.shared.security.signature import sign_dingtalk, sign_feishu
from hei_fastapi_ddd.types.business import BusinessError

logger = logging.getLogger(__name__)


async def send_push(title: str, content: str) -> None:
    """按 DEFAULT_MESSAGE_PUSH_ENGINE 推送文本消息。"""
    engine = (config_reader.get("DEFAULT_MESSAGE_PUSH_ENGINE") or "DINGTALK").strip().upper()
    text = f"{title}\n{content}" if title else content

    if engine == "DINGTALK":
        await _send_dingtalk(text)
    elif engine in {"LARK", "FEISHU"}:
        await _send_lark(text)
    elif engine in {"WECOM", "WECHAT_WORK", "WECHATWORK"}:
        await _send_wecom(text)
    else:
        raise BusinessError(f"Unsupported push engine: {engine}")


async def _send_dingtalk(text: str) -> None:
    """通过钉钉机器人 Webhook 推送文本消息（可选加签）。"""
    webhook = (config_reader.get("PUSH_DINGTALK_WEBHOOK") or "").strip()
    if not webhook:
        raise BusinessError("钉钉推送未配置: PUSH_DINGTALK_WEBHOOK")
    secret = (config_reader.get("PUSH_DINGTALK_SECRET") or "").strip()
    url = webhook
    if secret:
        timestamp, sign = sign_dingtalk(secret)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}timestamp={timestamp}&sign={sign}"

    payload = {"msgtype": "text", "text": {"content": text}}
    await _post_json(url, payload, "钉钉")


async def _send_lark(text: str) -> None:
    """通过飞书机器人 Webhook 推送文本消息（可选加签）。"""
    webhook = (config_reader.get("PUSH_LARK_WEBHOOK") or "").strip()
    if not webhook:
        raise BusinessError("飞书推送未配置: PUSH_LARK_WEBHOOK")
    secret = (config_reader.get("PUSH_LARK_SECRET") or "").strip()
    payload: dict = {
        "msg_type": "text",
        "content": {"text": text},
    }
    if secret:
        timestamp, sign = sign_feishu(secret)
        payload["timestamp"] = timestamp
        payload["sign"] = sign
    await _post_json(webhook, payload, "飞书")


async def _send_wecom(text: str) -> None:
    """通过企业微信机器人 Webhook 推送文本消息。"""
    webhook = (config_reader.get("PUSH_WECHAT_WORK_WEBHOOK") or "").strip()
    if not webhook:
        raise BusinessError("企业微信推送未配置: PUSH_WECHAT_WORK_WEBHOOK")
    payload = {"msgtype": "text", "text": {"content": text}}
    await _post_json(webhook, payload, "企业微信")


async def _post_json(url: str, payload: dict, label: str) -> None:
    """向 Webhook POST JSON，HTTP 异常统一转为业务错误。"""
    try:
        validate_outbound_url(url)
        client = get_http_client()
        resp = await client.post(url, json=payload)
        if resp.status_code >= 400:
            raise BusinessError(f"{label}推送失败: HTTP {resp.status_code}")
    except UnsafeUrlError as exc:
        raise BusinessError(f"{label}推送失败: URL 不安全: {exc}") from exc
    except BusinessError:
        raise
    except Exception as exc:
        logger.exception("%s push failed", label)
        raise BusinessError(f"{label}推送失败") from exc
