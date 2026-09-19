"""加载基础设施层任务处理器（避免 application 依赖 infrastructure）。"""

_loaded = False


def load_infrastructure_handlers() -> None:
    """导入 infra / 跨 BC 任务模块，触发 @job_handler 注册。"""
    global _loaded
    if _loaded:
        return
    _loaded = True
    from hei_fastapi_ddd.contexts.iam.infrastructure.jobs import (
        account_tasks as _account,  # noqa: F401
    )
    from hei_fastapi_ddd.contexts.sys.infrastructure.audit import (
        task_handlers as _audit,  # noqa: F401
    )
    from hei_fastapi_ddd.contexts.sys.infrastructure.banner import (
        task_handlers as _banner,  # noqa: F401
    )
    from hei_fastapi_ddd.contexts.sys.infrastructure.job import handlers as _job  # noqa: F401
