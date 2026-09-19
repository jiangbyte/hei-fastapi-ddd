""" Author: Charlie

应用工厂：组装中间件、异常处理、可观测性与路由，创建 FastAPI 应用。
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hei_fastapi_ddd.app.lifespan import lifespan
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.exceptions.handlers import (
    customize_openapi_error_responses,
    register_auth_root_callable,
    register_exception_handlers,
)
from hei_fastapi_ddd.shared.logger.setup import setup_logging
from hei_fastapi_ddd.shared.middleware.asgi_core import (
    AccessLogMiddleware,
    AuthContextMiddleware,
    TraceMiddleware,
)
from hei_fastapi_ddd.shared.middleware.asgi_rest import (
    AuthWhitelistMiddleware,
    OperationAuditMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from hei_fastapi_ddd.shared.middleware.csrf import CsrfProtectMiddleware
from hei_fastapi_ddd.shared.observability.manager import setup_observability
from hei_fastapi_ddd.shared.persistence.session import engine
from hei_fastapi_ddd.shared.schema.health import RootHealthResponse
from hei_fastapi_ddd.shared.web.schema import ApiResponse, success

logger = logging.getLogger(__name__)


def _add_cors(app: FastAPI) -> None:
    """安装 CORS 中间件，处理通配 origin 与 credentials 的兼容。"""
    origins = list(settings.cors.allow_origins)
    allow_credentials = settings.cors.allow_credentials
    if "*" in origins:
        origins = ["*"]
        allow_credentials = False
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用，组装中间件、路由与生命周期。"""
    setup_logging()

    # 1. 延迟导入路由，确保日志先初始化
    from hei_fastapi_ddd.app.routers import get_api_router

    api_router = get_api_router()

    # 2. 平台回调装配：认证依赖根与审计 outbox（避免 shared 硬依赖业务包）
    from hei_fastapi_ddd.shared.audit.queue import register_outbox_handlers
    from hei_fastapi_ddd.shared.deps import auth as auth_deps

    for root in (
        auth_deps.get_current_session,
        auth_deps.get_current_account,
        auth_deps.get_optional_session,
    ):
        register_auth_root_callable(root)

    try:
        from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.audit_outbox import (
            claim_pending_outbox,
            enqueue_outbox,
        )

        register_outbox_handlers(enqueue_outbox, claim_pending_outbox)
    except ImportError:
        logger.debug("audit outbox not registered yet")

    try:
        from hei_fastapi_ddd.contexts.sys.infrastructure.audit_event_handler import (
            register as register_audit_event_handler,
        )

        register_audit_event_handler()
    except ImportError:
        logger.debug("audit event handler not registered yet")

    try:
        from hei_fastapi_ddd.contexts.auth.infrastructure.session_event_handler import (
            register as register_session_event_handler,
        )

        register_session_event_handler()
    except ImportError:
        logger.debug("session event handler not registered yet")

    # 3. 构建 FastAPI 并按既定顺序安装中间件（后添加的更靠外）
    app = FastAPI(
        title=settings.app.name,
        debug=False,
        docs_url="/docs" if settings.swagger.enabled else None,
        redoc_url="/redoc" if settings.swagger.enabled else None,
        openapi_url="/openapi.json" if settings.swagger.enabled else None,
        lifespan=lifespan,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(OperationAuditMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthWhitelistMiddleware)
    app.add_middleware(AuthContextMiddleware)
    app.add_middleware(CsrfProtectMiddleware)
    app.add_middleware(TraceMiddleware)
    _add_cors(app)
    register_exception_handlers(app)
    customize_openapi_error_responses(app)
    setup_observability(app, engine=engine)

    @app.get("/", tags=["health"], response_model=ApiResponse[RootHealthResponse])
    async def root() -> ApiResponse[RootHealthResponse]:
        return success(RootHealthResponse(name=settings.app.name))

    app.include_router(api_router)
    logger.info("Application created with %d routes", len(app.routes))
    return app
