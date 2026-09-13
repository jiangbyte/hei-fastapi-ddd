""" Author: Charlie

Webhook 加签工具：钉钉 / 飞书（自定义机器人）签名算法，与官方文档保持一致。

- 钉钉: HMAC-SHA256(key=secret, msg="{timestamp}\n{secret}")，timestamp 为毫秒。
- 飞书: HMAC-SHA256(key="{timestamp}\n{secret}", msg="")，timestamp 为毫秒。

两套算法差异很大，复制实现极易出错（历史上曾出现飞书签名按钉钉方式
计算、时间戳用秒等问题），统一收敛在此处，调用方只消费 (timestamp, sign)。
"""
import base64
import hashlib
import hmac
import time
from urllib.parse import quote_plus


def now_timestamp_ms() -> str:
    """返回当前毫秒级时间戳字符串（钉钉/飞书签名均要求毫秒）。"""
    return str(round(time.time() * 1000))


def sign_dingtalk(secret: str, timestamp: str | None = None) -> tuple[str, str]:
    """计算钉钉自定义机器人加签，返回 (timestamp, sign)。

    官方算法：以 secret 为密钥，对 "{timestamp}\n{secret}" 做 HMAC-SHA256。
    """
    ts = timestamp or now_timestamp_ms()
    string_to_sign = f"{ts}\n{secret}"
    digest = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return ts, quote_plus(base64.b64encode(digest).decode("utf-8"))


def sign_feishu(secret: str, timestamp: str | None = None) -> tuple[str, str]:
    """计算飞书/自定义机器人加签，返回 (timestamp, sign)。

    官方算法：以 "{timestamp}\n{secret}" 为密钥、空消息体做 HMAC-SHA256，
    与钉钉的 key/msg 用法相反，勿混用。
    """
    ts = timestamp or now_timestamp_ms()
    string_to_sign = f"{ts}\n{secret}"
    digest = hmac.new(
        string_to_sign.encode("utf-8"),
        b"",
        digestmod=hashlib.sha256,
    ).digest()
    return ts, quote_plus(base64.b64encode(digest).decode("utf-8"))
