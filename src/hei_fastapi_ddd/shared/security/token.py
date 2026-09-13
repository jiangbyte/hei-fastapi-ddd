""" Author: Charlie

不透明 token 生成工具。
"""

import secrets


def generate_token() -> str:
    """生成 URL 安全的随机不透明 token（32 字节）。"""
    return secrets.token_urlsafe(32)
