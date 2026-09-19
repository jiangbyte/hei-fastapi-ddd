""" Author: Charlie

常用业务异常：按 HTTP 语义预置状态码，供服务层直接抛出。

业务模块可在此基础上派生更细分的异常，或在抛出时覆盖 code。
"""

from hei_fastapi_ddd.types.base import AppError


class BusinessError(AppError):
    """通用业务错误（400）。"""

    status_code = 400
    code = 400


class AuthenticationError(AppError):
    """认证失败（401）：未登录或凭证无效。"""

    status_code = 401
    code = 401


class AuthorizationError(AppError):
    """授权失败（403）：已登录但无权限访问。"""

    status_code = 403
    code = 403


class NotFoundError(AppError):
    """资源不存在（404）。"""

    status_code = 404
    code = 404


class ConflictError(AppError):
    """资源冲突（409）：如唯一约束冲突。"""

    status_code = 409
    code = 409
