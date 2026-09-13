""" Author: Charlie

代码生成前端输出路径：默认指向姊妹仓库 hei-admin，可通过环境变量覆盖。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path, PurePosixPath

from hei_fastapi_ddd.shared.config.settings import PROJECT_ROOT

_DEFAULT_FRONTEND_REL = Path("..") / "hei-admin"


def _resolve_frontend_root() -> Path:
    raw = os.environ.get("CODEGEN_FRONTEND_ROOT", "").strip()
    if raw:
        path = Path(raw)
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        return path
    return (PROJECT_ROOT / _DEFAULT_FRONTEND_REL).resolve()


@lru_cache(maxsize=1)
def get_codegen_frontend_root() -> Path:
    """返回 hei-admin（或配置项）根目录绝对路径。"""
    return _resolve_frontend_root()


def frontend_views_prefix() -> str:
    """前端 views 相对项目根的路径（用于预览路径展示）。"""
    root = get_codegen_frontend_root()
    rel = Path("src/views")
    try:
        return str(rel.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str((root / rel).relative_to(PROJECT_ROOT)).replace("\\", "/")


def frontend_api_prefix() -> str:
    """前端 api 相对项目根的路径。"""
    root = get_codegen_frontend_root()
    rel = Path("src/api")
    try:
        return str((root / rel).relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(rel).replace("\\", "/")


def frontend_view_path(component_path: str) -> str:
    """生成 views 下组件预览路径（相对 fastapi 项目根）。"""
    rel = PurePosixPath("src/views") / component_path.strip("/")
    try:
        return str((get_codegen_frontend_root() / rel).relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        )
    except ValueError:
        return str(rel)


def frontend_api_file_path(plan_component_path: str, entity_name: str) -> str:
    """生成 api 文件预览路径（相对 fastapi 项目根）。"""
    from hei_fastapi_ddd.contexts.sys.application.codegen.templates import snake_case

    component_path = PurePosixPath(plan_component_path.strip("/"))
    parts = component_path.parts
    api_root = get_codegen_frontend_root() / "src/api"
    if len(parts) >= 2 and parts[-1] == "index.vue":
        rel = PurePosixPath(*parts[:-1])
        api_rel = rel.with_suffix(".ts")
    else:
        api_rel = PurePosixPath(f"{snake_case(entity_name)}.ts")
    full = api_root / api_rel
    try:
        return str(full.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(PurePosixPath("src/api") / api_rel)


def frontend_api_export_path(api_file: str) -> str:
    """从 api 文件路径得到 index 导出行所需的相对 api 路径。"""
    api_prefix = str((get_codegen_frontend_root() / "src/api").resolve())
    normalized = api_file.replace("\\", "/")
    if normalized.startswith(api_prefix.replace("\\", "/")):
        rel = PurePosixPath(normalized[len(api_prefix):].lstrip("/"))
    else:
        marker = "src/api/"
        idx = normalized.find(marker)
        if idx >= 0:
            rel = PurePosixPath(normalized[idx + len(marker):])
        else:
            rel = PurePosixPath(normalized)
    return f"./{rel.with_suffix('').as_posix()}"


def frontend_api_index_append_path() -> str:
    """index.ts.append 预览路径。"""
    try:
        return str(
            (get_codegen_frontend_root() / "src/api/index.ts.append").relative_to(PROJECT_ROOT)
        ).replace("\\", "/")
    except ValueError:
        return "src/api/index.ts.append"


def frontend_api_index_rel() -> Path:
    """index.ts 相对 fastapi 项目根的路径（用于 apply）。"""
    try:
        return (get_codegen_frontend_root() / "src/api/index.ts").relative_to(PROJECT_ROOT)
    except ValueError:
        return Path("src/api/index.ts")
