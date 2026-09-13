""" Author: Charlie """

from unittest.mock import AsyncMock

import pytest

from hei_fastapi_ddd.shared.config.enums import AccountType
from hei_fastapi_ddd.contexts.auth.domain.policy import get_auth_options, get_login_policy


def test_login_policy_defaults(monkeypatch):
    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.auth.domain.policy.config_reader.get_bool",
        lambda key, default=False: default,
    )
    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.auth.domain.policy.config_reader.get_int",
        lambda key, default=0: default,
    )
    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.auth.domain.policy.config_reader.get",
        lambda key, default=None: default,
    )
    policy = get_login_policy(AccountType.ADMIN)
    assert policy.allow_email is True
    assert policy.phone_no_user_policy == "DENY"
    opts = get_auth_options(AccountType.PORTAL)
    assert opts.allow_account is True
    assert opts.password_change_verify_method == "OLD_PASSWORD"


def test_cloud_sdk_adapters_importable():
    """官方云 SDK 适配器模块可导入（不再有手写签名函数）。"""
    from hei_fastapi_ddd.shared.cloud.aliyun import send_aliyun_mail, send_aliyun_sms
    from hei_fastapi_ddd.shared.cloud.tencent import send_tencent_mail, send_tencent_sms

    assert callable(send_aliyun_sms)
    assert callable(send_aliyun_mail)
    assert callable(send_tencent_sms)
    assert callable(send_tencent_mail)


@pytest.mark.asyncio
async def test_send_mail_local_uses_ssl_flags(monkeypatch):
    from hei_fastapi_ddd.shared.email import sender as email_sender

    calls = {}

    def fake_get(key, default=None):
        data = {
            "DEFAULT_EMAIL_ENGINE": "LOCAL",
            "MAIL_LOCAL_HOST": "smtp.test",
            "MAIL_LOCAL_FROM_EMAIL": "a@b.c",
            "MAIL_LOCAL_FROM_NAME": "n",
            "MAIL_LOCAL_USERNAME": "u",
            "MAIL_LOCAL_PASSWORD": "p",
        }
        return data.get(key, default)

    monkeypatch.setattr(email_sender.config_reader, "get", fake_get)
    monkeypatch.setattr(email_sender.config_reader, "get_int", lambda k, d=0: 465 if "PORT" in k else d)
    monkeypatch.setattr(
        email_sender.config_reader,
        "get_bool",
        lambda k, d=False: True if "SSL" in k or "AUTH" in k else False,
    )

    def fake_send_sync(message, **kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(email_sender, "_send_sync", fake_send_sync)
    monkeypatch.setattr(email_sender.asyncio, "to_thread", AsyncMock(side_effect=lambda fn, *a, **k: fn(*a, **k)))

    await email_sender.send_mail("to@x.com", "s", "b")
    assert calls["use_ssl"] is True
    assert calls["auth_required"] is True


@pytest.mark.asyncio
async def test_send_sms_aliyun_calls_rpc(monkeypatch):
    from hei_fastapi_ddd.shared.sms import sender as sms_sender

    monkeypatch.setattr(
        sms_sender.config_reader,
        "get",
        lambda key, default=None: {
            "DEFAULT_SMS_ENGINE": "ALIYUN",
            "SMS_ALIYUN_ACCESS_KEY_ID": "id",
            "SMS_ALIYUN_ACCESS_KEY_SECRET": "secret",
            "SMS_ALIYUN_SIGN_NAME": "sign",
        }.get(key, default),
    )
    send = AsyncMock()
    monkeypatch.setattr(sms_sender, "send_aliyun_sms", send)
    await sms_sender.send_sms("13800138000", "SMS_1", {"code": "123456"})
    assert send.await_count == 1
    kwargs = send.await_args.kwargs
    assert kwargs["sign_name"] == "sign"
    assert kwargs["template_param"] == {"code": "123456"}
