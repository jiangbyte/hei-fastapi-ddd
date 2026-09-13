""" Author: Charlie

跨模块通用小 DTO。
"""

from hei_fastapi_ddd.shared.schema.base import ApiSchema


class IdNameResponse(ApiSchema):
    """通用 ID/名称回显项。"""

    id: str
    name: str
