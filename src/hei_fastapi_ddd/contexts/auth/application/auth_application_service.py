""" Author: Charlie

认证应用服务门面：按登录、注册、绑定、重置、生命周期拆分 mixin，对外仍暴露 AuthService。
"""

from hei_fastapi_ddd.contexts.auth.application.base import AuthServiceBase
from hei_fastapi_ddd.contexts.auth.application.base import _audit_record as _audit_record
from hei_fastapi_ddd.contexts.auth.application.base import session_expires_in as session_expires_in
from hei_fastapi_ddd.contexts.auth.application.bind_service import BindCodeMixin
from hei_fastapi_ddd.contexts.auth.application.lifecycle_service import LifecycleMixin
from hei_fastapi_ddd.contexts.auth.application.login_service import LoginMixin
from hei_fastapi_ddd.contexts.auth.application.password_reset_service import PasswordResetMixin
from hei_fastapi_ddd.contexts.auth.application.register_service import RegisterMixin


class AuthService(
    LoginMixin,
    RegisterMixin,
    BindCodeMixin,
    PasswordResetMixin,
    LifecycleMixin,
    AuthServiceBase,
):
    """认证服务门面，保持既有调用方 `AuthService(db)` 不变。"""


__all__ = ["AuthService", "session_expires_in", "_audit_record"]
