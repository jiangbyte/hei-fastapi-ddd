""" Author: Charlie

阿里云云渠道（短信 dysmsapi / 邮件 DirectMail）。

基于官方 SDK ``alibabacloud_dysmsapi20170525`` / ``alibabacloud_dm20151123``，
SDK 为同步客户端，异步调用放到线程池执行。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from alibabacloud_dm20151123 import models as dm_models
from alibabacloud_dm20151123.client import Client as DmClient
from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
from alibabacloud_tea_openapi import models as open_api_models

# 各产品接口的业务成功码（dysmsapi 为 OK，DirectMail 为 Success）。
_SUCCESS_CODES = {"OK", "SUCCESS"}


def _make_config(endpoint: str, access_key_id: str, access_key_secret: str) -> open_api_models.Config:
    """构造指定接入点的 OpenAPI 客户端配置。"""
    config = open_api_models.Config(access_key_id=access_key_id, access_key_secret=access_key_secret)
    config.endpoint = endpoint
    return config


def _ensure_ok(code: str | None, message: str | None) -> None:
    """业务码非成功时抛出错误（SDK 只负责传输层异常，业务错误码在响应体内）。"""
    if code and str(code).upper() not in _SUCCESS_CODES:
        raise RuntimeError(f"Aliyun error: {code} {message}")


async def send_aliyun_sms(
    *,
    access_key_id: str,
    access_key_secret: str,
    sign_name: str,
    phone: str,
    template_code: str,
    template_param: dict[str, Any],
) -> None:
    """通过阿里云短信（dysmsapi SendSms）发送模板短信。"""
    request = dysmsapi_models.SendSmsRequest(
        phone_numbers=phone,
        sign_name=sign_name,
        template_code=template_code,
        template_param=json.dumps(template_param, ensure_ascii=False),
    )

    def _call():
        client = DysmsapiClient(
            _make_config("dysmsapi.aliyuncs.com", access_key_id, access_key_secret)
        )
        return client.send_sms(request).body

    body = await asyncio.to_thread(_call)
    _ensure_ok(body.code, body.message)


async def send_aliyun_mail(
    *,
    access_key_id: str,
    access_key_secret: str,
    account_name: str,
    from_alias: str | None,
    to_email: str,
    subject: str,
    body_text: str,
) -> None:
    """通过阿里云 DirectMail（SingleSendMail）发送文本邮件。"""
    request = dm_models.SingleSendMailRequest(
        account_name=account_name,
        address_type="1",
        reply_to_address="false",
        to_address=to_email,
        subject=subject,
        text_body=body_text,
        from_alias=from_alias,
    )

    def _call():
        client = DmClient(_make_config("dm.aliyuncs.com", access_key_id, access_key_secret))
        return client.single_send_mail(request).body

    body = await asyncio.to_thread(_call)
    _ensure_ok(body.code, body.message)
