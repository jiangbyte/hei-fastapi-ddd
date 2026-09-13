""" Author: Charlie

应用配置：集中定义数据库、Redis、认证、存储、可观测性等子系统的设置项。

所有配置类均基于 pydantic-settings，支持环境变量与 .env 文件覆盖，
并通过 get_settings() 以进程级缓存提供全局单例。
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from hei_fastapi_ddd.shared.config.enums import StorageProvider

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class AppSettings(BaseSettings):
    """应用基础设置：名称、监听地址、进程角色与时区。"""

    model_config = SettingsConfigDict(extra="ignore")

    name: str = "hei-fastapi-ddd"
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = True
    config_crypto_key: str = ""
    timezone: str = "Asia/Shanghai"
    trusted_proxy_ips: list[str] = []


class DatabaseSettings(BaseSettings):
    """数据库连接池设置（SQLAlchemy async）。"""

    url: str = "mysql+aiomysql://root:123456@127.0.0.1:3306/hei_fastapi?charset=utf8mb4"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout_seconds: float = 30.0
    pool_recycle_seconds: int = 1800
    pool_pre_ping: bool = True


class AuditSettings(BaseSettings):
    """操作审计队列与日志保留设置。"""

    operation_queue_size: int = 1000
    operation_shutdown_timeout_seconds: float = 5.0
    login_retention_days: int = 180
    operation_retention_days: int = 365
    cleanup_batch_size: int = 1000


class RedisSettings(BaseSettings):
    """Redis 连接设置。"""

    url: str = "redis://localhost:6379/0"
    max_connections: int = 1000


class AuthSettings(BaseSettings):
    """认证与会话设置：token 时效、登录锁定、Cookie 会话等。"""

    token_name: str = "Authorization"
    token_ttl_seconds: int = 60 * 60 * 4
    token_ttl_short_seconds: int = 60 * 60 * 2
    portal_register_enabled: bool = True
    login_failure_window_seconds: int = 15 * 60
    login_account_max_failures: int = 5
    login_ip_max_failures: int = 30
    login_lock_seconds: int = 15 * 60
    password_reset_token_ttl_seconds: int = 10 * 60
    default_password: str = ""
    captcha_ttl_seconds: int = 5 * 60
    password_crypto_key_ttl_seconds: int = 10 * 60
    # 0 = 禁用（本地/开发）。容器/生产类栈常设为 1800。
    session_idle_timeout_seconds: int = 0
    session_bind_ip: bool = True
    session_bind_user_agent: bool = False
    max_concurrent_sessions: int = 5
    # Cookie 优先的 Web 会话；原生客户端可在 token_name 头发送不透明 token
    # （非 HTTP Bearer）。Cookie 名与 token_name 同为 Authorization；
    # 登录/登出时 Path 取自请求路径父级；session_cookie_path 仅用于清理旧版 Path=/。
    session_cookie_enabled: bool = True
    session_cookie_name: str = "Authorization"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    session_cookie_path: str = "/"
    # 额外鉴权豁免路径（精确或 fnmatch），与内置白名单合并。
    auth_whitelist: list[str] = []


class SecretsSettings(BaseSettings):
    """密钥后端设置：Fernet 本地密钥或 Vault KV v2。"""

    model_config = SettingsConfigDict(extra="ignore")

    # fernet = APP__CONFIG_CRYPTO_KEY；vault = 从 KV v2 加载 Fernet 密钥
    backend: str = "fernet"
    vault_addr: str = ""
    vault_token: str = ""
    vault_mount: str = "secret"
    vault_path: str = "hei/fernet"
    vault_key_field: str = "fernet_key"
    vault_timeout_seconds: float = 5.0
    # 生产加固：APP__DEBUG=false 时，除非显式豁免，否则拒绝仅 Fernet 后端。
    require_vault: bool = False
    allow_fernet_in_prod: bool = True


class MailSettings(BaseSettings):
    """SMTP 邮件发送设置。"""

    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = ""
    from_name: str = "hei-fastapi-ddd"
    use_tls: bool = True
    timeout_seconds: float = 10.0


class CorsSettings(BaseSettings):
    """跨域（CORS）白名单设置。"""

    allow_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5163",
        "http://127.0.0.1:5163",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    allow_credentials: bool = True
    allow_methods: list[str] = [
        "GET",
        "POST",
        "OPTIONS",
    ]
    allow_headers: list[str] = [
        "Authorization",
        "Content-Type",
        "X-Request-Id",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-HEI-CSRF",
    ]


class JobSettings(BaseSettings):
    """内置任务调度设置：DB 驱动轮询（sys_job 表），进程内 asyncio 后台任务。"""

    model_config = SettingsConfigDict(extra="ignore")

    # 调度扫描间隔（毫秒），对齐 hei-boot hei.job.scan-interval-ms。
    scan_interval_ms: int = 1000
    # 最大并发执行任务数，对齐 hei-boot hei.job.pool-size。
    pool_size: int = 4
    # 任务执行日志保留天数 / 分批删除大小，对齐 hei-boot hei.job.log.*。
    log_retention_days: int = 30
    log_batch_size: int = 1000


class StorageSettings(BaseSettings):
    """文件存储设置：对象存储（MinIO/RustFS/OSS/COS）及上传限制。"""

    provider: StorageProvider = StorageProvider.MINIO
    bucket: str = ""
    endpoint: str = ""
    access_key: str = ""
    secret_key: str = ""
    region: str = ""
    use_ssl: bool = False
    presign_expire_seconds: int = 3600
    base_url: str = ""
    bucket_public: bool = False
    upload_max_bytes: int = 10 * 1024 * 1024
    upload_allowed_content_types: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "text/plain",
        "video/mp4",
        "video/webm",
        "video/quicktime",
    ]
    upload_allowed_extensions: list[str] = [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".pdf",
        ".txt",
        ".mp4",
        ".webm",
        ".mov",
    ]
    upload_denied_extensions: list[str] = [
        ".exe",
        ".bat",
        ".cmd",
        ".sh",
        ".js",
        ".html",
        ".htm",
        ".svg",
        ".php",
        ".py",
        ".jar",
    ]
    upload_category_max_length: int = 64


class IdGeneratorSettings(BaseSettings):
    """雪花 ID 生成器 worker/datacenter 设置。"""

    # 0 = 从 hostname/pid 自动派生唯一 worker（多副本推荐）
    worker_id: int = 0
    datacenter_id: int = 1


class SwaggerSettings(BaseSettings):
    """Swagger 文档开关。"""

    enabled: bool = False


class ObservabilitySettings(BaseSettings):
    """可观测性设置：日志、指标、链路追踪。"""

    enabled: bool = False
    service_name: str = "hei-fastapi-ddd"
    service_version: str = "1.1.0-beta"
    environment: str = "dev"
    log_enabled: bool = True
    log_level: str = "INFO"
    log_json: bool = False
    log_dir: str = "logs"
    log_file_max_mb: int = 100
    metrics_enabled: bool = False
    metrics_path: str = "/metrics"
    tracing_enabled: bool = False
    otlp_enabled: bool = False
    otlp_endpoint: str = ""
    sample_ratio: float = 1.0
    db_observability_enabled: bool = False
    http_client_observability_enabled: bool = False


class AuditAlertSettings(BaseSettings):
    """审计告警规则设置。"""

    enabled: bool = False
    notify_email: bool = True
    notify_push: bool = True
    notify_custom_webhook: bool = False
    webhook_url: str = ""
    webhook_secret: str = ""
    analysis_interval_seconds: int = 300
    alert_cooldown_seconds: int = 1800
    rule_brute_force: bool = True
    rule_unusual_hours: bool = True
    rule_sensitive_ops: bool = True
    rule_bulk_delete: bool = True
    rule_ip_anomaly: bool = True
    brute_force_threshold: int = 10
    bulk_delete_threshold: int = 20
    ip_anomaly_threshold: int = 3


class ProfileIdentitySettings(BaseSettings):
    """实名认证（profile identity）设置。"""

    model_config = SettingsConfigDict(extra="ignore")

    # 可选覆盖 APP__CONFIG_CRYPTO_KEY；为空时回退全局 config_crypto_key
    crypto_key: str = ""
    third_party_init_url: str = ""
    third_party_callback_url: str = ""
    third_party_api_key: str = ""
    third_party_timeout_seconds: float = 30.0


class PasswordPolicySettings(BaseSettings):
    """密码策略设置：强度、过期、历史检查。"""

    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    expire_days: int = 90
    history_check_count: int = 5
    common_password_check: bool = True
    # UPPER_SNAKE complexity: NO_LIMIT | DIGITS_AND_LETTERS | ...
    complexity: str = "DIGITS_UPPER_LOWER_SPECIAL"
    max_consecutive_chars: int = 3
    forbid_user_info: bool = True
    forbid_historical: bool = True
    expiry_warning_days: int = 3


class Settings(BaseSettings):
    """聚合根设置，嵌套各子系统配置并从环境变量/.env 加载。"""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.local"),
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    audit: AuditSettings = Field(default_factory=AuditSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    secrets: SecretsSettings = Field(default_factory=SecretsSettings)
    mail: MailSettings = Field(default_factory=MailSettings)
    cors: CorsSettings = Field(default_factory=CorsSettings)
    job: JobSettings = Field(default_factory=JobSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    password_policy: PasswordPolicySettings = Field(default_factory=PasswordPolicySettings)
    profile_identity: ProfileIdentitySettings = Field(default_factory=ProfileIdentitySettings)
    audit_alert: AuditAlertSettings = Field(default_factory=AuditAlertSettings)
    id_generator: IdGeneratorSettings = Field(default_factory=IdGeneratorSettings)
    swagger: SwaggerSettings = Field(default_factory=SwaggerSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    module_configs: dict[str, Any] = Field(default_factory=dict, exclude=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回进程级缓存的 Settings 单例。"""
    return Settings()


settings = get_settings()
