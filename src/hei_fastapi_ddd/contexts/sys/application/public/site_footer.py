"""站点页脚配置解析。"""

from hei_fastapi_ddd.shared.config.reader import config_reader


def _trim(value: str | None) -> str:
    return (value or "").strip()


def resolve_site_footer() -> dict[str, str]:
    """从 sys_config 读取版权与备案信息（应用层 DTO）。"""
    return {
        "copyright_text": _trim(config_reader.get("COPYRIGHT_TEXT")),
        "copyright_url": _trim(config_reader.get("COPYRIGHT_URL")),
        "icp_number": _trim(config_reader.get("SITE_ICP_NUMBER")),
        "icp_url": _trim(config_reader.get("SITE_ICP_URL")),
        "psb_number": _trim(config_reader.get("SITE_PSB_NUMBER")),
        "psb_url": _trim(config_reader.get("SITE_PSB_URL")),
    }
