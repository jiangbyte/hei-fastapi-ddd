""" Author: Charlie

邮件发送：按 DEFAULT_EMAIL_ENGINE 分发到本地 SMTP、阿里云、腾讯云三种渠道。

支持模板渲染（{{变量}}）与同步 SMTP 发送（放到线程池执行以免阻塞事件循环）。
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

from hei_fastapi_ddd.shared.cloud.aliyun import send_aliyun_mail
from hei_fastapi_ddd.shared.cloud.tencent import send_tencent_mail
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.types.business import BusinessError

logger = logging.getLogger(__name__)


def is_mail_configured() -> bool:
    """当前邮件引擎所需关键配置是否齐全（未配置则不应尝试发送）。"""
    engine = (config_reader.get("DEFAULT_EMAIL_ENGINE") or "LOCAL").strip().upper()
    if engine == "LOCAL":
        host = (config_reader.get("MAIL_LOCAL_HOST") or settings.mail.host or "").strip()
        from_email = (
            config_reader.get("MAIL_LOCAL_FROM_EMAIL") or settings.mail.from_email or ""
        ).strip()
        return bool(host and from_email)
    if engine == "ALIYUN":
        return all(
            (config_reader.get(key) or "").strip()
            for key in (
                "MAIL_ALIYUN_ACCESS_KEY_ID",
                "MAIL_ALIYUN_ACCESS_KEY_SECRET",
                "MAIL_ALIYUN_ACCOUNT_NAME",
            )
        )
    if engine == "TENCENT":
        return all(
            (config_reader.get(key) or "").strip()
            for key in (
                "MAIL_TENCENT_SECRET_ID",
                "MAIL_TENCENT_SECRET_KEY",
                "MAIL_TENCENT_FROM_EMAIL",
            )
        )
    return False


async def send_mail(to_email: str, subject: str, body: str) -> None:
    """按 DEFAULT_EMAIL_ENGINE 发送纯文本邮件。"""
    engine = (config_reader.get("DEFAULT_EMAIL_ENGINE") or "LOCAL").strip().upper()
    if engine == "LOCAL":
        await _send_local_smtp(to_email, subject, body)
        return
    if engine == "ALIYUN":
        await _send_aliyun_mail(to_email, subject, body)
        return
    if engine == "TENCENT":
        await _send_tencent_mail(to_email, subject, body)
        return
    raise BusinessError(f"Unsupported email engine: {engine}")


async def send_templated_mail(scene: str, to_email: str, variables: dict[str, Any]) -> None:
    """按 MAIL_TEMPLATE_{SCENE} 渲染并发送。"""
    tmpl = config_reader.get_mail_template(scene)
    subject = tmpl["subject"] or f"{settings.app.name}"
    body = tmpl["body"] or ""
    subject = _render(subject, variables)
    body = _render(body, variables)
    if not subject.strip() and not body.strip():
        raise BusinessError(f"Mail template missing: MAIL_TEMPLATE_{scene}")
    await send_mail(to_email, subject, body)


def _render(text: str, variables: dict[str, Any]) -> str:
    """用 ``{{key}}`` 占位符替换变量，缺失变量按替换不到原样保留。"""
    out = text
    for key, value in variables.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out


async def _send_local_smtp(to_email: str, subject: str, body: str) -> None:
    """构造邮件并通过本地 SMTP 发送（同步部分放到线程池）。"""
    host = (config_reader.get("MAIL_LOCAL_HOST") or settings.mail.host or "").strip()
    port = config_reader.get_int("MAIL_LOCAL_PORT", settings.mail.port)
    from_email = (config_reader.get("MAIL_LOCAL_FROM_EMAIL") or settings.mail.from_email or "").strip()
    from_name = (config_reader.get("MAIL_LOCAL_FROM_NAME") or settings.mail.from_name or "").strip()
    if not host or not from_email:
        raise BusinessError("Mail service is not configured")

    message = EmailMessage()
    message["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    use_ssl = config_reader.get_bool("MAIL_LOCAL_USE_SSL", False)
    use_starttls = config_reader.get_bool(
        "MAIL_LOCAL_USE_STARTTLS",
        settings.mail.use_tls,
    )
    auth_required = config_reader.get_bool(
        "MAIL_LOCAL_AUTH_REQUIRED",
        bool((config_reader.get("MAIL_LOCAL_USERNAME") or settings.mail.username or "").strip()),
    )
    username = (config_reader.get("MAIL_LOCAL_USERNAME") or settings.mail.username or "").strip()
    password = config_reader.get("MAIL_LOCAL_PASSWORD") or settings.mail.password or ""
    timeout = settings.mail.timeout_seconds

    await asyncio.to_thread(
        _send_sync,
        message,
        host=host,
        port=port,
        use_ssl=use_ssl,
        use_starttls=use_starttls,
        auth_required=auth_required,
        username=username,
        password=password,
        timeout=timeout,
    )


def _send_sync(
    message: EmailMessage,
    *,
    host: str,
    port: int,
    use_ssl: bool,
    use_starttls: bool,
    auth_required: bool,
    username: str,
    password: str,
    timeout: float,
) -> None:
    """同步执行 SMTP 发送，支持 SSL/TLS/STARTTLS 与登录鉴权。"""
    try:
        context = ssl.create_default_context()
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as smtp:
                if auth_required and username:
                    smtp.login(username, password)
                smtp.send_message(message)
            return
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            if use_starttls:
                smtp.starttls(context=context)
            if auth_required and username:
                smtp.login(username, password)
            smtp.send_message(message)
    except OSError as exc:
        raise BusinessError("Failed to send email") from exc
    except smtplib.SMTPException as exc:
        raise BusinessError("Failed to send email") from exc


async def _send_aliyun_mail(to_email: str, subject: str, body: str) -> None:
    """通过阿里云 DirectMail 发送邮件。"""
    access_key_id = _require("MAIL_ALIYUN_ACCESS_KEY_ID")
    access_key_secret = _require("MAIL_ALIYUN_ACCESS_KEY_SECRET")
    account_name = _require("MAIL_ALIYUN_ACCOUNT_NAME")
    from_alias = (config_reader.get("MAIL_LOCAL_FROM_NAME") or settings.mail.from_name or "").strip()
    try:
        await send_aliyun_mail(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            account_name=account_name,
            from_alias=from_alias or None,
            to_email=to_email,
            subject=subject,
            body_text=body,
        )
    except Exception as exc:
        logger.exception("Aliyun mail failed")
        raise BusinessError("Failed to send email via Aliyun") from exc


async def _send_tencent_mail(to_email: str, subject: str, body: str) -> None:
    """通过腾讯云 SES 发送邮件。"""
    secret_id = _require("MAIL_TENCENT_SECRET_ID")
    secret_key = _require("MAIL_TENCENT_SECRET_KEY")
    from_email = _require("MAIL_TENCENT_FROM_EMAIL")
    region = (config_reader.get("MAIL_TENCENT_REGION") or "ap-guangzhou").strip()
    try:
        await send_tencent_mail(
            secret_id=secret_id,
            secret_key=secret_key,
            region=region,
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            body_text=body,
        )
    except Exception as exc:
        logger.exception("Tencent mail failed")
        raise BusinessError("Failed to send email via Tencent") from exc


def _require(key: str) -> str:
    value = (config_reader.get(key) or "").strip()
    if not value:
        raise BusinessError(f"邮件引擎未配置: {key}")
    return value
