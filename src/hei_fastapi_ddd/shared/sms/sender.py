""" Author: Charlie

短信发送适配器（按 DEFAULT_SMS_ENGINE 分发）。
"""
from __future__ import annotations

import logging
from typing import Any

from hei_fastapi_ddd.shared.cloud.aliyun import send_aliyun_sms
from hei_fastapi_ddd.shared.cloud.tencent import send_tencent_sms
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.exceptions.business import BusinessError

logger = logging.getLogger(__name__)


async def send_sms(phone: str, template_code: str, params: dict[str, Any]) -> None:
    """按默认短信引擎发送模板短信。"""
    engine = (config_reader.get("DEFAULT_SMS_ENGINE") or "ALIYUN").strip().upper()
    if engine == "ALIYUN":
        await _send_aliyun(phone, template_code, params)
        return
    if engine == "TENCENT":
        await _send_tencent(phone, template_code, params)
        return
    raise BusinessError(f"Unsupported SMS engine: {engine}")


async def send_templated_sms(scene: str, phone: str, variables: dict[str, Any]) -> None:
    """按 SMS_TEMPLATE_{SCENE} 取模板编号并发送。"""
    tmpl = config_reader.get_sms_template(scene)
    code = (tmpl.get("code") or "").strip()
    if not code:
        raise BusinessError(f"SMS template code missing: SMS_TEMPLATE_{scene}")
    await send_sms(phone, code, variables)


async def _send_aliyun(phone: str, template_code: str, params: dict[str, Any]) -> None:
    """通过阿里云短信（dysmsapi）发送模板短信。"""
    access_key_id = _require("SMS_ALIYUN_ACCESS_KEY_ID")
    access_key_secret = _require("SMS_ALIYUN_ACCESS_KEY_SECRET")
    sign_name = _require("SMS_ALIYUN_SIGN_NAME")
    try:
        await send_aliyun_sms(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            sign_name=sign_name,
            phone=phone,
            template_code=template_code,
            template_param=params,
        )
    except Exception as exc:
        logger.exception("Aliyun SMS failed")
        raise BusinessError("Failed to send SMS via Aliyun") from exc


async def _send_tencent(phone: str, template_code: str, params: dict[str, Any]) -> None:
    """通过腾讯云短信（sms）发送模板短信。"""
    secret_id = _require("SMS_TENCENT_SECRET_ID")
    secret_key = _require("SMS_TENCENT_SECRET_KEY")
    sdk_app_id = _require("SMS_TENCENT_SDK_APP_ID")
    sign_name = _require("SMS_TENCENT_SIGN_NAME")
    region = (config_reader.get("SMS_TENCENT_REGION") or "ap-guangzhou").strip()
    # 腾讯云模板参数按顺序传字符串数组；约定用 code/变量值排序：优先 code
    template_param_set = [str(params[k]) for k in sorted(params.keys())]
    if "code" in params:
        template_param_set = [str(params["code"])] + [
            str(params[k]) for k in sorted(params.keys()) if k != "code"
        ]
    phone_number = phone if phone.startswith("+") else f"+86{phone}"
    try:
        await send_tencent_sms(
            secret_id=secret_id,
            secret_key=secret_key,
            region=region,
            sdk_app_id=sdk_app_id,
            sign_name=sign_name,
            template_id=template_code,
            phone_numbers=[phone_number],
            template_param_set=template_param_set,
        )
    except Exception as exc:
        logger.exception("Tencent SMS failed")
        raise BusinessError("Failed to send SMS via Tencent") from exc


def _require(key: str) -> str:
    value = (config_reader.get(key) or "").strip()
    if not value:
        raise BusinessError(f"短信引擎未配置: {key}")
    return value
