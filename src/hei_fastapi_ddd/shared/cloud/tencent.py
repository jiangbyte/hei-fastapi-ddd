""" Author: Charlie

腾讯云云渠道（短信 sms / SES 邮件）。

基于官方 SDK ``tencentcloud-sdk-python-sms`` / ``tencentcloud-sdk-python-ses``，
SDK 为同步客户端，异步调用放到线程池执行。
"""

from __future__ import annotations

import asyncio

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ses.v20201002 import models as ses_models
from tencentcloud.ses.v20201002 import ses_client
from tencentcloud.sms.v20210111 import models as sms_models
from tencentcloud.sms.v20210111 import sms_client

from hei_fastapi_ddd.types.business import BusinessError


def _make_credential(secret_id: str, secret_key: str) -> credential.Credential:
    """构造腾讯云凭证。"""
    return credential.Credential(secret_id, secret_key)


async def _call_guarded(call, label: str) -> None:
    """在线程池执行 SDK 调用，SDK 异常转统一业务错误。"""
    try:
        await asyncio.to_thread(call)
    except TencentCloudSDKException as exc:
        raise BusinessError(f"Failed to send {label}") from exc


async def send_tencent_sms(
    *,
    secret_id: str,
    secret_key: str,
    region: str,
    sdk_app_id: str,
    sign_name: str,
    template_id: str,
    phone_numbers: list[str],
    template_param_set: list[str],
) -> None:
    """通过腾讯云短信（sms SendSms）发送模板短信。"""
    request = sms_models.SendSmsRequest()
    request.SmsSdkAppId = sdk_app_id
    request.SignName = sign_name
    request.TemplateId = template_id
    request.PhoneNumberSet = phone_numbers
    request.TemplateParamSet = template_param_set

    def _call():
        sms_client.SmsClient(_make_credential(secret_id, secret_key), region).SendSms(request)

    await _call_guarded(_call, "SMS via Tencent")


async def send_tencent_mail(
    *,
    secret_id: str,
    secret_key: str,
    region: str,
    from_email: str,
    to_email: str,
    subject: str,
    body_text: str,
) -> None:
    """通过腾讯云 SES（SendEmail）发送文本邮件。"""
    request = ses_models.SendEmailRequest()
    request.FromEmailAddress = from_email
    request.Destination = [to_email]
    request.Subject = subject
    request.Simple = {"Text": body_text}

    def _call():
        ses_client.SesClient(_make_credential(secret_id, secret_key), region).SendEmail(request)

    await _call_guarded(_call, "email via Tencent")
