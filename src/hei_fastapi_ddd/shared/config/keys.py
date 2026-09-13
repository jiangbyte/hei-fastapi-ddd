""" Author: Charlie

sys_config key → settings 字段显式映射（UPPER_SNAKE keys）。
"""

from __future__ import annotations

# (config_key, settings_group, field_name)
SETTINGS_KEY_MAP: list[tuple[str, str, str]] = [
    # auth
    ("AUTH_TOKEN_TTL_SECONDS", "auth", "token_ttl_seconds"),
    ("AUTH_PASSWORD_RESET_TOKEN_TTL_SECONDS", "auth", "password_reset_token_ttl_seconds"),
    ("AUTH_LOGIN_FAILURE_WINDOW_SECONDS", "auth", "login_failure_window_seconds"),
    ("AUTH_LOGIN_ACCOUNT_MAX_FAILURES", "auth", "login_account_max_failures"),
    ("AUTH_LOGIN_IP_MAX_FAILURES", "auth", "login_ip_max_failures"),
    ("AUTH_LOGIN_LOCK_SECONDS", "auth", "login_lock_seconds"),
    ("AUTH_REGISTER_PORTAL_ENABLED", "auth", "portal_register_enabled"),
    ("AUTH_DEFAULT_PASSWORD", "auth", "default_password"),
    # mail (LOCAL SMTP mapped to settings.mail)
    ("MAIL_LOCAL_HOST", "mail", "host"),
    ("MAIL_LOCAL_PORT", "mail", "port"),
    ("MAIL_LOCAL_USERNAME", "mail", "username"),
    ("MAIL_LOCAL_PASSWORD", "mail", "password"),
    ("MAIL_LOCAL_FROM_EMAIL", "mail", "from_email"),
    ("MAIL_LOCAL_FROM_NAME", "mail", "from_name"),
    ("MAIL_LOCAL_USE_STARTTLS", "mail", "use_tls"),
    # upload / storage limits
    ("STORAGE_UPLOAD_MAX_BYTES", "storage", "upload_max_bytes"),
    ("STORAGE_PRESIGN_EXPIRE_SECONDS", "storage", "presign_expire_seconds"),
    ("STORAGE_UPLOAD_ALLOWED_CONTENT_TYPES", "storage", "upload_allowed_content_types"),
    ("STORAGE_UPLOAD_ALLOWED_EXTENSIONS", "storage", "upload_allowed_extensions"),
    ("STORAGE_UPLOAD_DENIED_EXTENSIONS", "storage", "upload_denied_extensions"),
    ("STORAGE_UPLOAD_CATEGORY_MAX_LENGTH", "storage", "upload_category_max_length"),
    # audit alert
    ("AUDIT_ALERT_ENABLED", "audit_alert", "enabled"),
    ("AUDIT_ALERT_NOTIFY_EMAIL", "audit_alert", "notify_email"),
    ("AUDIT_ALERT_NOTIFY_PUSH", "audit_alert", "notify_push"),
    ("AUDIT_ALERT_NOTIFY_CUSTOM_WEBHOOK", "audit_alert", "notify_custom_webhook"),
    ("AUDIT_ALERT_WEBHOOK_URL", "audit_alert", "webhook_url"),
    ("AUDIT_ALERT_WEBHOOK_SECRET", "audit_alert", "webhook_secret"),
    ("AUDIT_ALERT_ANALYSIS_INTERVAL_SECONDS", "audit_alert", "analysis_interval_seconds"),
    ("AUDIT_ALERT_ALERT_COOLDOWN_SECONDS", "audit_alert", "alert_cooldown_seconds"),
    ("AUDIT_ALERT_RULE_BRUTE_FORCE", "audit_alert", "rule_brute_force"),
    ("AUDIT_ALERT_RULE_UNUSUAL_HOURS", "audit_alert", "rule_unusual_hours"),
    ("AUDIT_ALERT_RULE_SENSITIVE_OPS", "audit_alert", "rule_sensitive_ops"),
    ("AUDIT_ALERT_RULE_BULK_DELETE", "audit_alert", "rule_bulk_delete"),
    ("AUDIT_ALERT_RULE_IP_ANOMALY", "audit_alert", "rule_ip_anomaly"),
    ("AUDIT_ALERT_BRUTE_FORCE_THRESHOLD", "audit_alert", "brute_force_threshold"),
    ("AUDIT_ALERT_BULK_DELETE_THRESHOLD", "audit_alert", "bulk_delete_threshold"),
    ("AUDIT_ALERT_IP_ANOMALY_THRESHOLD", "audit_alert", "ip_anomaly_threshold"),
    # password policy
    ("PASSWORD_MIN_LENGTH", "password_policy", "min_length"),
    ("PASSWORD_MAX_LENGTH", "password_policy", "max_length"),
    ("PASSWORD_VALIDITY_DAYS", "password_policy", "expire_days"),
    ("PASSWORD_HISTORY_CHECK_COUNT", "password_policy", "history_check_count"),
    ("PASSWORD_FORBID_WEAK_LIST", "password_policy", "common_password_check"),
    ("PASSWORD_MAX_CONSECUTIVE_CHARS", "password_policy", "max_consecutive_chars"),
    ("PASSWORD_FORBID_USER_INFO", "password_policy", "forbid_user_info"),
    ("PASSWORD_FORBID_HISTORICAL", "password_policy", "forbid_historical"),
    ("PASSWORD_EXPIRY_WARNING_DAYS", "password_policy", "expiry_warning_days"),
    ("PASSWORD_COMPLEXITY", "password_policy", "complexity"),
]

SENSITIVE_CONFIG_KEYS: frozenset[str] = frozenset(
    {
        "AUTH_DEFAULT_PASSWORD",
        "AUDIT_ALERT_WEBHOOK_SECRET",
        "MAIL_LOCAL_PASSWORD",
        "MAIL_ALIYUN_ACCESS_KEY_SECRET",
        "MAIL_TENCENT_SECRET_KEY",
        "SMS_ALIYUN_ACCESS_KEY_SECRET",
        "SMS_TENCENT_SECRET_KEY",
        "PUSH_DINGTALK_SECRET",
        "PUSH_LARK_SECRET",
        "STORAGE_MINIO_ACCESS_KEY",
        "STORAGE_MINIO_SECRET_KEY",
        "STORAGE_RUSTFS_ACCESS_KEY",
        "STORAGE_RUSTFS_SECRET_KEY",
        "STORAGE_ALIYUN_ACCESS_KEY",
        "STORAGE_ALIYUN_SECRET_KEY",
        "STORAGE_TENCENT_ACCESS_KEY",
        "STORAGE_TENCENT_SECRET_KEY",
    }
)
# 需要加密存储的敏感配置键集合（密码、Secret、AK/SK 等）。
