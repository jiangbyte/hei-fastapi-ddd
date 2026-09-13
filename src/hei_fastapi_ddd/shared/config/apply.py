""" Author: Charlie

从 DB 配置表回写运行期 settings 的显式映射。
"""
from hei_fastapi_ddd.shared.config.coerce import coerce_config_value
from hei_fastapi_ddd.shared.config.enums import StorageProvider
from hei_fastapi_ddd.shared.config.keys import SETTINGS_KEY_MAP
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.config.settings import settings


def apply_sys_config() -> None:
    """从 sys_config 表覆盖运行期 settings（仅映射已声明字段）。"""
    groups = {
        "storage": settings.storage,
        "mail": settings.mail,
        "auth": settings.auth,
        "audit_alert": settings.audit_alert,
        "password_policy": settings.password_policy,
    }
    for config_key, group_name, field_name in SETTINGS_KEY_MAP:
        settings_obj = groups.get(group_name)
        if settings_obj is None:
            continue
        raw = config_reader.get(config_key)
        if raw is None:
            continue
        field_info = settings_obj.model_fields.get(field_name)
        if field_info is None:
            continue
        value = coerce_config_value(raw, field_info.annotation)
        if value is not None:
            setattr(settings_obj, field_name, value)


def apply_storage_config() -> None:
    """校验 DEFAULT_FILE_ENGINE 与默认引擎必要字段。"""
    engine = config_reader.get("DEFAULT_FILE_ENGINE")
    if not engine:
        raise RuntimeError(
            "DEFAULT_FILE_ENGINE is missing in sys_config (table empty or seed not imported). "
            "Restore seeds with: mysql ... < scripts/hei_fastapi.sql "
            "(safe re-import: no DROP TABLE). Or set DEFAULT_FILE_ENGINE via admin after seed."
        )
    default = config_reader.get_default_storage()
    if default is None:
        raise RuntimeError(
            f"DEFAULT_FILE_ENGINE={engine!r} does not map to a known storage provider."
        )
    missing: list[str] = []
    if not default.bucket:
        missing.append("bucket")
    if default.provider != StorageProvider.S3 and not default.endpoint:
        missing.append("endpoint")
    if default.provider == StorageProvider.S3 and not (default.region or default.endpoint):
        missing.append("region/endpoint")
    if missing:
        raise RuntimeError(
            f"Default {default.provider.value} storage is missing required fields: "
            + ", ".join(missing)
        )


def apply_all_config() -> None:
    """顺序应用所有 DB 配置覆盖到 settings。"""
    apply_storage_config()
    apply_sys_config()
