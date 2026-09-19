""" Author: Charlie

Codegen 工作区 apply 辅助测试。
"""
from pathlib import Path

from hei_fastapi_ddd.contexts.sys.api.codegen_schemas import CodegenPreviewFile
from hei_fastapi_ddd.contexts.sys.application.codegen.apply import (
    apply_preview_files,
    extract_export_aliases,
    merge_api_index_export,
)


def test_merge_api_index_export_is_idempotent():
    index = "export * as authApi from './auth'\nexport * as cgTestActivityApi from './biz/cg-test-activity'\n"
    block = (
        "// 由 HEI 代码生成器生成。\n"
        "export * as cgTestActivityApi from './biz/cg-test-activity'\n"
    )
    merged, changed = merge_api_index_export(index, block)
    assert changed is False
    assert merged == index


def test_merge_api_index_export_appends_missing_alias():
    index = "export * as authApi from './auth'\n"
    block = "export * as demoApi from './biz/demo'\n"
    merged, changed = merge_api_index_export(index, block)
    assert changed is True
    assert "export * as demoApi from './biz/demo'" in merged
    assert "authApi" in extract_export_aliases(merged)


def test_apply_preview_files_merges_append_and_writes_others(tmp_path: Path):
    api_index = tmp_path / "src/api/index.ts"
    api_index.parent.mkdir(parents=True)
    api_index.write_text("export * as authApi from './auth'\n", encoding="utf-8")

    files = [
        CodegenPreviewFile(
            path="app/modules/biz/demo/router.py",
            language="python",
            content="router = None\n",
        ),
        CodegenPreviewFile(
            path="src/api/index.ts.append",
            language="typescript",
            content="export * as demoApi from './biz/demo'\n",
        ),
        CodegenPreviewFile(
            path="src/api/index.ts.append",
            language="typescript",
            content="export * as demoApi from './biz/demo'\n",
        ),
    ]
    import os

    os.environ["CODEGEN_FRONTEND_ROOT"] = str(tmp_path)
    from hei_fastapi_ddd.contexts.sys.application.codegen.paths import get_codegen_frontend_root

    get_codegen_frontend_root.cache_clear()

    result = apply_preview_files(files, tmp_path)
    assert (tmp_path / "app/modules/biz/demo/router.py").read_text(
        encoding="utf-8"
    ) == "router = None\n"
    text = api_index.read_text(encoding="utf-8")
    assert text.count("demoApi") == 1
    assert "src/api/index.ts" in result.merged
    assert result.skipped  # 第二次 append 因已存在而跳过
    get_codegen_frontend_root.cache_clear()
    os.environ.pop("CODEGEN_FRONTEND_ROOT", None)
