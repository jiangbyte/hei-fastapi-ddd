"""Author: Charlie

ASGI CSRF 双提交校验中间件。
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from hei_fastapi_ddd.shared.security.csrf import validate_csrf
from hei_fastapi_ddd.shared.web.errors import asgi_error_response


class CsrfProtectMiddleware:
    """当请求携带会话 Cookie 时，对非安全方法校验双提交 CSRF。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive=receive)
        err = validate_csrf(request)
        if err:
            await asgi_error_response(scope, receive, send, status_code=403, message=err)
            return
        await self.app(scope, receive, send)
