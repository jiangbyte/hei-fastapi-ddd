""" Author: Charlie

Content-Disposition 构建（ASCII fallback + RFC5987 filename*），对齐 hei-boot。
"""

from __future__ import annotations

from urllib.parse import quote


def content_disposition_attachment(original_name: str | None) -> str:
    """构建 attachment Content-Disposition 头。"""
    name = (original_name or "").strip() or "download"
    ascii_name = "".join(ch if 0x20 <= ord(ch) <= 0x7E and ch != '"' else "_" for ch in name)
    if not ascii_name.strip("_"):
        ascii_name = "download"
    encoded = quote(name, safe="")
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded}'
