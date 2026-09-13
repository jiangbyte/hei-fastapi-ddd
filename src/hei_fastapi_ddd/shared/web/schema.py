""" Author: Charlie

统一 API 响应模型：所有接口成功/失败均返回 ApiResponse / ApiErrorResponse 外壳。
"""

from typing import Generic, TypeVar

from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireInt

T = TypeVar("T")


class ApiResponse(ApiSchema, Generic[T]):
    """统一 API 响应外壳，约束接口输出结构的一致性。"""

    code: WireInt = 200
    message: str = "success"
    data: T | None = None


class ApiErrorResponse(ApiSchema):
    """统一错误响应模型，所有异常响应均返回相同的外壳结构。"""

    code: WireInt
    message: str
    data: None = None


def success(data: T | None = None, message: str = "success") -> ApiResponse[T]:
    """生成成功响应模型，供路由返回统一结构并走 Pydantic 序列化。"""
    return ApiResponse[T](code=200, message=message, data=data)
