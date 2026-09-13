""" Author: Charlie

数据脱敏工具——防止日志、审计与 API 响应泄露敏感信息。

等保要求：非必要场景不得以明文暴露敏感个人信息。
"""
import re


def mask_email(email: str | None) -> str | None:
    """邮箱脱敏：j***@example.com"""
    if not email:
        return email
    at_idx = email.find("@")
    if at_idx < 2:
        return email
    return email[0] + "***" + email[at_idx:]


def mask_phone(phone: str | None) -> str | None:
    """手机号脱敏：138****1234"""
    if not phone or len(phone) < 7:
        return phone
    return phone[:3] + "****" + phone[-4:]


def mask_identifier(value: str | None) -> str | None:
    """自动识别并脱敏邮箱或手机号；无法识别时返回原值。"""
    if not value:
        return value
    if "@" in value:
        return mask_email(value)
    if re.fullmatch(r"1\d{10}", value):
        return mask_phone(value)
    return value
