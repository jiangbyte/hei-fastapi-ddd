""" Author: Charlie """

from hei_fastapi_ddd.shared.security.auth_whitelist import (
    BUILTIN_AUTH_WHITELIST,
    clear_auth_whitelist_cache,
    is_auth_whitelisted,
)


def test_builtin_whitelist_matches_login_and_health():
    clear_auth_whitelist_cache()
    assert is_auth_whitelisted("/api/v1/admin/login")
    assert is_auth_whitelisted("/api/v1/portal/captcha")
    assert is_auth_whitelisted("/api/v1/internal/health/live")
    assert not is_auth_whitelisted("/api/v1/files")
    assert not is_auth_whitelisted("/api/v1/files/2026/07/25/demo.png")
    assert is_auth_whitelisted("/api/v1/portal/sys/banners/list")
    assert not is_auth_whitelisted("/api/v1/admin/sys/banners/create")
    # 版本通配：升到 v2 时认证/公开路径仍应放行
    assert is_auth_whitelisted("/api/v2/admin/login")
    assert is_auth_whitelisted("/api/v2/portal/sys/banners/list")
    assert not is_auth_whitelisted("/api/v2/files/demo.png")


def test_configured_whitelist_extends_builtin(monkeypatch):
    clear_auth_whitelist_cache()
    monkeypatch.setattr(
        "hei_fastapi_ddd.shared.security.auth_whitelist.settings.auth.auth_whitelist",
        ["/api/v1/custom/*"],
        raising=False,
    )
    # settings.auth 为嵌套模型 — 通过 object patch
    from hei_fastapi_ddd.shared.config.settings import settings

    monkeypatch.setattr(settings.auth, "auth_whitelist", ["/api/v1/custom/*"])
    clear_auth_whitelist_cache()
    assert is_auth_whitelisted("/api/v1/custom/foo")
    assert is_auth_whitelisted("/api/v1/admin/login")
    clear_auth_whitelist_cache()


def test_builtin_whitelist_nonempty():
    assert len(BUILTIN_AUTH_WHITELIST) > 10
