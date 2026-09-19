""" Author: Charlie

应用入口：创建 ASGI 应用实例供服务器加载。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 以脚本方式直接运行时，确保 src 目录在 sys.path 上。
if __package__ in {None, ""}:
    package_dir = Path(__file__).resolve().parent
    src_root = package_dir.parent
    sys.path = [path for path in sys.path if Path(path or ".").resolve() != package_dir]
    sys.path.insert(0, str(src_root))

from hei_fastapi_ddd.app.factory import create_app

app = create_app()
