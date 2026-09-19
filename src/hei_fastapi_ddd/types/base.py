""" Author: Charlie

异常体系基类：所有业务异常继承自 AppError，并携带 HTTP 状态码与业务码。

异常处理器在 hei_fastapi_ddd.shared.exceptions.handlers 中统一捕获并按此结构响应。
"""


class AppError(Exception):
    """应用异常基类，附加 status_code 与业务 code，供统一异常处理出口使用。"""

    status_code = 500
    code = 500

    def __init__(self, message: str):
        """以可读文案构造异常，并缓存到 message 供响应拼装使用。"""
        super().__init__(message)
        self.message = message
