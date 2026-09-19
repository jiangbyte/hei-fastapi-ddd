""" Author: Charlie

将代码生成预览文件写入工作区，低侵入合并。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from hei_fastapi_ddd.contexts.sys.application.codegen.dto import CodegenPreviewFile
from hei_fastapi_ddd.contexts.sys.application.codegen.paths import frontend_api_index_rel


def api_index_rel() -> Path:
    """hei-admin src/api/index.ts 相对 fastapi 项目根的路径。"""
    return frontend_api_index_rel()
_EXPORT_AS_RE = re.compile(r"export\s+\*\s+as\s+(\w+)\s+from\s+")


@dataclass
class ApplyResult:
    """应用预览文件的结果统计：已写入、已合并、已跳过。"""

    written: list[str] = field(default_factory=list)
    merged: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def extract_export_aliases(text: str) -> set[str]:
    """提取 index.ts 中 ``export * as xxx from`` 的别名集合。"""
    return set(_EXPORT_AS_RE.findall(text))


def merge_api_index_export(index_text: str, export_block: str) -> tuple[str, bool]:
    """追加尚未存在的代码生成 API 导出行。

    返回 ``(new_text, changed)``。
    """
    block = export_block.strip()
    if not block:
        return index_text, False

    existing = extract_export_aliases(index_text)
    lines_to_add: list[str] = []
    pending_comments: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = _EXPORT_AS_RE.search(stripped)
        if match is None:
            # 仅当下方有新导出时保留非导出行。
            pending_comments.append(line.rstrip())
            continue
        alias = match.group(1)
        if alias in existing:
            pending_comments.clear()
            continue
        lines_to_add.extend(pending_comments)
        pending_comments.clear()
        lines_to_add.append(line.rstrip())
        existing.add(alias)

    if not lines_to_add:
        return index_text, False

    body = index_text.rstrip()
    addition = "\n".join(lines_to_add)
    if body:
        return f"{body}\n{addition}\n", True
    return f"{addition}\n", True


def is_api_index_append(path: str) -> bool:
    """判断路径是否为 API 索引追加文件（index.ts.append）。"""
    normalized = path.replace("\\", "/")
    return normalized.endswith("index.ts.append") or normalized.endswith("/api/index.ts.append")


def is_wiring_append(path: str) -> bool:
    """判断路径是否为 biz wiring 追加片段。"""
    normalized = path.replace("\\", "/")
    return normalized.endswith("/infrastructure/wiring.py.append") or normalized.endswith(
        "wiring.py.append"
    )


def apply_preview_files(
    files: list[CodegenPreviewFile],
    root: Path,
    *,
    skip_menu_sql: bool = False,
) -> ApplyResult:
    """在 ``root`` 下物化预览文件。

    ``*.index.ts.append`` 幂等合并到 hei-admin ``src/api/index.ts``；
    ``wiring.py.append`` 追加到 biz ``infrastructure/wiring.py``。
    """
    result = ApplyResult()
    root = root.resolve()
    for item in files:
        rel = item.path.replace("\\", "/")
        if is_api_index_append(rel):
            index_rel = api_index_rel()
            index_path = root / index_rel
            current = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
            merged, changed = merge_api_index_export(current, item.content)
            if changed:
                index_path.parent.mkdir(parents=True, exist_ok=True)
                index_path.write_text(merged, encoding="utf-8", newline="\n")
                result.merged.append(str(index_rel.as_posix()))
            else:
                result.skipped.append(str(index_rel.as_posix()))
            continue

        if is_wiring_append(rel):
            # 1. 定位 wiring 目标文件
            # 2. 片段未出现则追加，避免重复生成
            wiring_rel = Path(rel[: -len(".append")])
            wiring_path = root / wiring_rel
            snippet = item.content.strip()
            current = wiring_path.read_text(encoding="utf-8") if wiring_path.exists() else ""
            marker = snippet.splitlines()[0] if snippet else ""
            if marker and marker in current:
                result.skipped.append(str(wiring_rel.as_posix()))
            else:
                wiring_path.parent.mkdir(parents=True, exist_ok=True)
                body = current.rstrip()
                wiring_path.write_text(
                    f"{body}\n\n{snippet}\n" if body else f"{snippet}\n",
                    encoding="utf-8",
                    newline="\n",
                )
                result.merged.append(str(wiring_rel.as_posix()))
            continue

        if skip_menu_sql and rel.endswith("_menu_permission.sql"):
            result.skipped.append(rel)
            continue

        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"path escapes output root: {rel}") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item.content, encoding="utf-8", newline="\n")
        result.written.append(rel)
    return result
