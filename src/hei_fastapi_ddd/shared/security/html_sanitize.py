"""Author: Charlie

对存储型 HTML 做轻量消毒（剥离 script / 事件属性 / 危险 URL）。
"""

from __future__ import annotations

import re

_SCRIPT = re.compile(r"(?is)<script\b[^>]*>.*?</script\s*>")
_STYLE = re.compile(r"(?is)<style\b[^>]*>.*?</style\s*>")
_IFRAME = re.compile(r"(?is)<iframe\b[^>]*>.*?</iframe\s*>")
_OBJECT = re.compile(r"(?is)<object\b[^>]*>.*?</object\s*>")
_EMBED = re.compile(r"(?is)<embed\b[^>]*/?>")
_EVENT_ATTR = re.compile(r"""(?i)\s+on[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""")
_DANGER_HREF = re.compile(
    r"""(?i)\s(href|src|xlink:href|action|formaction)\s*=\s*("|')\s*(javascript|data|vbscript)\s*:"""
)


def sanitize_html(content_type: str | None, content: str | None) -> str | None:
    """若 content_type 为 HTML 则消毒；其它类型原样返回。"""
    if content is None:
        return None
    if not content_type or content_type.strip().upper() != "HTML":
        return content
    out = content
    out = _SCRIPT.sub("", out)
    out = _STYLE.sub("", out)
    out = _IFRAME.sub("", out)
    out = _OBJECT.sub("", out)
    out = _EMBED.sub("", out)
    out = _EVENT_ATTR.sub("", out)
    out = _DANGER_HREF.sub(r" \1=\2#blocked", out)
    return out
