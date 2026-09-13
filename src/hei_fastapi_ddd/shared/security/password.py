""" Author: Charlie

密码哈希工具：统一使用 bcrypt 进行密码哈希与校验。

同步 API 供测试与种子数据使用；异步路径必须走 ``*_async``，
将 CPU 密集的 bcrypt 放到线程池，避免阻塞事件循环。
"""

from __future__ import annotations

import asyncio

import bcrypt


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希（同步，勿在 async 请求路径直接调用）。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """校验明文密码与 bcrypt 哈希值是否匹配（同步）。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


async def hash_password_async(password: str) -> str:
    """在线程池中执行 bcrypt 哈希，供 async 服务使用。"""
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(password: str, hashed_password: str) -> bool:
    """在线程池中执行 bcrypt 校验，供 async 服务使用。"""
    return await asyncio.to_thread(verify_password, password, hashed_password)
