""" Author: Charlie

展示图相关 Schema：创建/更新载荷、管理端分页查询与公开端列表查询。
"""

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from hei_fastapi_ddd.shared.config.enums import AccountType, StatusEnum
from hei_fastapi_ddd.shared.web.pagination import PageQuery
from hei_fastapi_ddd.shared.schema.base import ApiSchema
from hei_fastapi_ddd.shared.schema.wire import WireInt
from hei_fastapi_ddd.shared.security.safe_link import UnsafeLinkError, validate_banner_link
from hei_fastapi_ddd.contexts.sys.domain.banner.enums import BannerLinkType

_ALLOWED_ACCOUNT_TYPES = {item.value for item in AccountType}


class BannerCreateRequest(ApiSchema):
    """展示图创建请求。"""

    title: str = Field(min_length=1, max_length=255)
    image: str = Field(min_length=1, max_length=500)
    url: str | None = Field(default=None, max_length=500)
    link_type: BannerLinkType = BannerLinkType.URL
    summary: str | None = Field(default=None, max_length=500)
    description: str | None = None
    category: str = Field(min_length=1, max_length=32)
    type: str = Field(min_length=1, max_length=32)
    position: str = Field(min_length=1, max_length=32)
    target_account_types: list[str] = Field(default_factory=list)
    sort: WireInt = 0
    status: StatusEnum = StatusEnum.ENABLED
    start_at: datetime | None = None
    end_at: datetime | None = None

    @field_validator("target_account_types", mode="before")
    @classmethod
    def normalize_target_account_types(cls, value: object) -> list[str]:
        """将目标账户类型规范化为大写字符串列表（支持单值字符串与数组）。"""
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise ValueError("目标账户类型必须是数组")
        return [str(item).strip().upper() for item in value if str(item).strip()]

    @model_validator(mode="after")
    def validate_target_account_types(self):
        """校验目标账户类型合法并去重（空列表放行，对齐 hei-boot 默认空数组）。"""
        types = list(dict.fromkeys(self.target_account_types))
        invalid = [item for item in types if item not in _ALLOWED_ACCOUNT_TYPES]
        if invalid:
            raise ValueError(f"目标账户类型无效: {', '.join(invalid)}")
        self.target_account_types = types
        try:
            link_type = (
                self.link_type.value
                if isinstance(self.link_type, BannerLinkType)
                else str(self.link_type or "URL")
            )
            validate_banner_link(link_type, self.url)
        except UnsafeLinkError as exc:
            raise ValueError(str(exc)) from exc
        return self


class BannerUpdateRequest(BannerCreateRequest):
    """展示图更新请求，在创建字段基础上增加主键。"""

    id: str = Field(min_length=1, max_length=64)


class BannerAdminPageQuery(PageQuery):
    """展示图管理端分页查询参数（target_account_type 为自由字符串，对齐 hei-boot）。"""

    target_account_type: str | None = Field(default=None, max_length=32)
    category: str | None = Field(default=None, max_length=32)
    type: str | None = Field(default=None, max_length=32)
    position: str | None = Field(default=None, max_length=32)
    status: str | None = Field(default=None, max_length=32)


class BannerPublicListQuery(ApiSchema):
    """展示图公开端列表查询参数。"""

    position: str = Field(min_length=1, max_length=32)
    category: str | None = Field(default=None, max_length=32)
    type: str | None = Field(default=None, max_length=32)


class SysBannerSchema(ApiSchema):
    """展示图响应模型，含图片 URL 与创建/更新人昵称。"""

    id: str
    title: str
    image: str
    image_url: str | None = None
    url: str | None = None
    link_type: BannerLinkType | str
    summary: str | None = None
    description: str | None = None
    category: str
    type: str
    position: str
    target_account_types: list[str] = Field(default_factory=list)
    sort: WireInt
    interaction_count: WireInt
    status: StatusEnum | str
    start_at: datetime | None = None
    end_at: datetime | None = None
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime
    updated_by: str | None = None
