""" Author: Charlie

系统配置读取器：启动时从 sys_config 表全量加载配置到内存快照，并提供类型化读取入口。

同时从配置键构建各存储提供方的 StorageConfig 快照，支持按默认/指定/提供方查询。
"""

import json
from dataclasses import asdict

from sqlalchemy import select

from hei_fastapi_ddd.shared.config.crypto import decrypt_config_value
from hei_fastapi_ddd.shared.config.enums import StorageProvider
from hei_fastapi_ddd.shared.persistence.models.sys_config import SysConfig
from hei_fastapi_ddd.shared.persistence.session import get_session_factory
from hei_fastapi_ddd.shared.storage.config import StorageConfig
from hei_fastapi_ddd.shared.storage.engines import (
    PROVIDER_DISPLAY_NAMES,
    config_key,
    engine_to_provider,
)


class ConfigReader:
    """系统配置读取器，启动时从 DB 全量加载配置到不可变快照。"""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}
        self._storage_configs: dict[str, StorageConfig] = {}
        self._default_storage_id: str | None = None
        self._version = 0

    async def load_all(self) -> None:
        """从 DB 全量加载配置到内存缓存，成功后原子替换当前快照。"""
        cache: dict[str, str] = {}
        factory = get_session_factory()
        async with factory() as db:
            async with db as session:
                stmt = select(SysConfig).where(SysConfig.config_value.isnot(None))
                rows = (await session.execute(stmt)).scalars().all()
                for row in rows:
                    cache[row.config_key] = decrypt_config_value(row.config_key, row.config_value)
        storage_configs, default_storage_id = _build_storage_snapshot(cache)
        self._cache = cache
        self._storage_configs = storage_configs
        self._default_storage_id = default_storage_id
        self._version += 1

    async def reload(self) -> None:
        """重新加载（管理后台修改配置后调用）。"""
        await self.load_all()
        from hei_fastapi_ddd.shared.config.apply import apply_sys_config
        from hei_fastapi_ddd.shared.storage.manager import clear_storage_cache

        apply_sys_config()
        clear_storage_cache()

    @property
    def version(self) -> int:
        """配置快照版本号，每次重载自增。"""
        return self._version

    def get_default_storage(self) -> StorageConfig | None:
        """返回默认存储配置，未设置时返回 None。"""
        if self._default_storage_id is None:
            return None
        return self._storage_configs.get(self._default_storage_id)

    def get_storage_config(self, config_id: str | None = None) -> StorageConfig | None:
        """按配置 ID 返回存储配置；ID 为空时回退到默认存储。"""
        if config_id is None:
            return self.get_default_storage()
        return self._storage_configs.get(config_id)

    def get_storage_config_by_provider(
        self,
        provider: str | StorageProvider,
    ) -> StorageConfig | None:
        """按存储提供方查找配置；优先精确匹配 ID，否则按 provider 字段匹配。"""
        provider_value = StorageProvider(provider)
        by_id = self._storage_configs.get(provider_value.value)
        if by_id is not None:
            return by_id
        # 兼容测试/过渡期：id 尚未等于 provider 时按 provider 字段匹配
        matches = [c for c in self._storage_configs.values() if c.provider == provider_value]
        if not matches:
            return None
        for config in matches:
            if config.is_default:
                return config
        return matches[0]

    def list_storage_configs(self) -> list[StorageConfig]:
        """返回全部存储配置列表。"""
        return list(self._storage_configs.values())

    def get_active_storage(self) -> dict | None:
        """返回默认存储配置的字典形式，无默认存储时返回 None。"""
        active = self.get_default_storage()
        return asdict(active) if active else None

    def get(self, key: str, default: str | None = None) -> str | None:
        """读取字符串配置值，缺失时返回默认值。"""
        return self._cache.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """读取整数配置值，解析失败时返回默认值。"""
        val = self._cache.get(key)
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """读取布尔配置值，按真值集合解析。"""
        val = self._cache.get(key)
        if val is None:
            return default
        return val.lower() in ("true", "1", "yes")

    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """读取 JSON 列表配置值，缺失或解析失败时返回默认列表。"""
        val = self._cache.get(key)
        if val is None:
            return default or []
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
            return default or []
        except (json.JSONDecodeError, TypeError):
            return default or []

    def get_json(self, key: str, default: dict | None = None) -> dict:
        """读取 JSON 对象配置值，缺失或解析失败时返回默认字典。"""
        val = self._cache.get(key)
        if val is None:
            return default or {}
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else (default or {})
        except (json.JSONDecodeError, TypeError):
            return default or {}

    def get_mail_template(self, scene: str) -> dict[str, str]:
        """读取指定场景的邮件模板（主题与正文）。"""
        data = self.get_json(f"MAIL_TEMPLATE_{scene}")
        return {
            "subject": str(data.get("subject") or ""),
            "body": str(data.get("body") or ""),
        }

    def get_sms_template(self, scene: str) -> dict[str, str]:
        """读取指定场景的短信模板（模板码与内容）。"""
        data = self.get_json(f"SMS_TEMPLATE_{scene}")
        return {
            "code": str(data.get("code") or ""),
            "content": str(data.get("content") or ""),
        }

    def raw_items(self) -> dict[str, str]:
        """返回配置缓存的一份拷贝。"""
        return dict(self._cache)


def _build_storage_snapshot(
    cache: dict[str, str],
) -> tuple[dict[str, StorageConfig], str | None]:
    """从配置键构建全部存储提供方快照并确定默认存储 ID。"""
    presign_expire_seconds = _coerce_int(cache.get("STORAGE_PRESIGN_EXPIRE_SECONDS"), 3600)
    default_provider = engine_to_provider(cache.get("DEFAULT_FILE_ENGINE"))
    default_id = default_provider.value if default_provider else None
    configs: dict[str, StorageConfig] = {}
    for provider in StorageProvider:
        configs[provider.value] = _storage_config_from_cache(
            cache,
            provider,
            is_default=(default_id == provider.value),
            presign_expire_seconds=presign_expire_seconds,
        )
    return configs, default_id


def _storage_config_from_cache(
    cache: dict[str, str],
    provider: StorageProvider,
    *,
    is_default: bool,
    presign_expire_seconds: int,
) -> StorageConfig:
    """从配置键构建单个存储提供方的 StorageConfig。"""

    def g(suffix: str, default: str = "") -> str:
        return cache.get(config_key(provider, suffix)) or default

    use_ssl_raw = g("USE_SSL", "FALSE")
    use_ssl = use_ssl_raw.lower() in ("true", "1", "yes")
    bucket_public_raw = g("BUCKET_PUBLIC", "FALSE")
    bucket_public = bucket_public_raw.lower() in ("true", "1", "yes")
    force_path_style = provider in {StorageProvider.MINIO, StorageProvider.RUSTFS}
    return StorageConfig(
        id=provider.value,
        name=PROVIDER_DISPLAY_NAMES.get(provider, provider.value),
        provider=provider,
        bucket=g("BUCKET"),
        endpoint=g("ENDPOINT"),
        access_key=g("ACCESS_KEY"),
        secret_key=g("SECRET_KEY"),
        region=g("REGION"),
        use_ssl=use_ssl,
        base_url=g("BASE_URL"),
        bucket_public=bucket_public,
        is_default=is_default,
        force_path_style=force_path_style,
        presign_expire_seconds=presign_expire_seconds,
    )


def _coerce_int(value: str | None, default: int) -> int:
    """解析整数，空值或失败时返回默认值。"""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


config_reader = ConfigReader()
# 进程级全局配置读取器单例。
