""" Author: Charlie

缓存键生成：集中定义登录会话、验证码、密码传输密钥等 Redis 键的命名规则。

统一的键名可避免各处硬编码，便于排查与清理。
"""


def login_token_key(token: str) -> str:
    """登录 token 对应的会话载荷键。"""
    return f"login:token:{token}"


def login_account_tokens_key(account_type: str, account_id: str) -> str:
    """某账户维度下的全部 token 集合键（用于踢下线）。"""
    return f"login:account:{account_type}:{account_id}"


def login_tokens_key() -> str:
    """全局在线 token 集合键。"""
    return "login:tokens"


def login_failure_account_key(account_type: str, account: str) -> str:
    """账户登录失败计数键。"""
    return f"login:failure:account:{account_type}:{account}"


def login_failure_ip_key(account_type: str, ip: str) -> str:
    """IP 登录失败计数键。"""
    return f"login:failure:ip:{account_type}:{ip}"


def login_lock_account_key(account_type: str, account: str) -> str:
    """账户登录锁定标记键。"""
    return f"login:lock:account:{account_type}:{account}"


def login_lock_ip_key(account_type: str, ip: str) -> str:
    """IP 登录锁定标记键。"""
    return f"login:lock:ip:{account_type}:{ip}"


def reset_password_otp_key(account_type: str, phone: str) -> str:
    """通过手机找回密码时的一次性验证码键（对齐 hei-boot reset password OTP）。"""
    return f"password:reset:otp:{account_type}:PHONE:{phone}"


def password_reset_token_key(token: str) -> str:
    """密码重置 token 键。"""
    return f"password:reset:{token}"


def job_run_lock_key(job_id: str) -> str:
    """任务执行互斥锁键（Redis 锁，防多实例重复执行）。"""
    return f"sys:job:run:{job_id}"


def login_otp_key(account_type: str, channel: str, target: str) -> str:
    """登录一次性验证码（OTP）键。"""
    return f"login:otp:{account_type}:{channel}:{target}"


def change_password_otp_key(account_type: str, channel: str, account_id: str) -> str:
    """修改密码一次性验证码（OTP）键。"""
    return f"password:change:otp:{account_type}:{channel}:{account_id}"


def bind_otp_key(account_type: str, channel: str, account_id: str) -> str:
    """绑定/换绑邮箱或手机号的一次性验证码（OTP）键。"""
    return f"user:bind:otp:{account_type}:{channel}:{account_id}"


def register_otp_key(channel: str, target: str) -> str:
    """门户注册通道（邮箱/手机）的一次性验证码（OTP）键。"""
    return f"user:register:otp:{channel}:{target}"


def password_expiry_notify_key(account_id: str) -> str:
    """密码即将过期通知去重键（24h，对齐 hei-boot auth:notify:password-expiring）。"""
    return f"auth:notify:password-expiring:{account_id}"


def captcha_key(captcha_id: str) -> str:
    """图形验证码键。"""
    return f"captcha:{captcha_id}"


def password_crypto_key(key_id: str) -> str:
    """一次性密码传输私钥键。"""
    return f"password:crypto:{key_id}"


def cache_key(name: str) -> str:
    """通用业务缓存键（前缀 Cache:）。"""
    return f"Cache:{name}"


def permission_resource_cache_key() -> str:
    """权限资源注册表缓存键。"""
    return cache_key("permission-resource")


def permission_resource_method_cache_key() -> str:
    """权限资源 HTTP 方法映射缓存键。"""
    return cache_key("permission-resource-method")


def banner_interaction_delta_key() -> str:
    """横幅交互增量计数键。"""
    return "banner:interaction:deltas"
