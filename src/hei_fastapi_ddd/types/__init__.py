"""跨层类型：业务异常基类与业务错误码。"""
from hei_fastapi_ddd.types.base import AppError
from hei_fastapi_ddd.types.business import *  # noqa: F403

__all__ = ["AppError"]
