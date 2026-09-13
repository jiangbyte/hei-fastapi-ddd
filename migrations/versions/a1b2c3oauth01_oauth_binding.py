""" Author: Charlie

三方登录：sys_account_oauth_binding 表 + OAUTH_PROVIDER 字典 + AUTH_OAUTH 配置种子。

对齐 hei-boot V5__account_oauth_binding.sql。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3oauth01"
down_revision: str | Sequence[str] | None = "27c193fc4b22"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------ 表
    op.create_table(
        "sys_account_oauth_binding",
        sa.Column("id", sa.String(length=64), nullable=False, comment="主键"),
        sa.Column("account_id", sa.String(length=64), nullable=False, comment="账户ID"),
        sa.Column("provider", sa.String(length=32), nullable=False, comment="提供商"),
        sa.Column("open_id", sa.String(length=128), nullable=False, comment="平台 openid"),
        sa.Column("union_id", sa.String(length=128), nullable=True, comment="微信 unionid"),
        sa.Column("nickname", sa.String(length=128), nullable=True, comment="平台昵称"),
        sa.Column("avatar", sa.Text(), nullable=True, comment="平台头像"),
        sa.Column("raw_profile", sa.JSON(), nullable=False, comment="平台原始资料 JSON"),
        sa.Column(
            "bound_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="绑定时间",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column("created_by", sa.String(length=64), nullable=True, comment="创建人"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("updated_by", sa.String(length=64), nullable=True, comment="更新人"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_account_oauth_binding")),
        sa.UniqueConstraint("provider", "open_id", name="uq_oauth_provider_open_id"),
        sa.UniqueConstraint("account_id", "provider", name="uq_oauth_account_provider"),
    )
    op.create_index(
        "idx_oauth_binding_account",
        "sys_account_oauth_binding",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "idx_oauth_binding_union",
        "sys_account_oauth_binding",
        ["union_id"],
        unique=False,
    )

    # ------------------------------------------------------------------ 字典
    dict_rows = [
        (
            "dict_oauth_provider",
            "OAUTH_PROVIDER",
            "三方登录提供商",
            "OAUTH_PROVIDER",
            None,
            "SYS",
            None,
            90,
        ),
        ("dict_oauth_github", "GITHUB", "GitHub", "GITHUB", None, "SYS", "dict_oauth_provider", 1),
        ("dict_oauth_gitee", "GITEE", "Gitee", "GITEE", None, "SYS", "dict_oauth_provider", 2),
        ("dict_oauth_qq", "QQ", "QQ", "QQ", None, "SYS", "dict_oauth_provider", 3),
        (
            "dict_oauth_wechat_open",
            "WECHAT_OPEN",
            "微信开放平台",
            "WECHAT_OPEN",
            None,
            "SYS",
            "dict_oauth_provider",
            4,
        ),
        (
            "dict_oauth_wechat_mp",
            "WECHAT_MP",
            "微信小程序",
            "WECHAT_MP",
            None,
            "SYS",
            "dict_oauth_provider",
            5,
        ),
    ]
    for row in dict_rows:
        _insert_dict(op, *row)

    # ------------------------------------------------------------------ 配置
    # (config_key, category, remark, sort, value_type, label, scope, scene)
    config_rows = [
        # 门户 × 提供商开关与凭据
        ("AUTH_OAUTH_PORTAL_GITHUB_ENABLED", "AUTH_OAUTH", "门户 GitHub 登录", 1, "BOOL", "启用", "PORTAL", "GITHUB", "FALSE"),
        ("AUTH_OAUTH_PORTAL_GITHUB_CLIENT_ID", "AUTH_OAUTH", "门户 GitHub ClientId", 2, "STRING", "Client ID", "PORTAL", "GITHUB", ""),
        ("AUTH_OAUTH_PORTAL_GITHUB_CLIENT_SECRET", "AUTH_OAUTH", "门户 GitHub ClientSecret", 3, "STRING", "Client Secret", "PORTAL", "GITHUB", ""),
        ("AUTH_OAUTH_PORTAL_GITHUB_REDIRECT_URI", "AUTH_OAUTH", "门户 GitHub 回调", 4, "STRING", "Redirect URI", "PORTAL", "GITHUB", ""),
        ("AUTH_OAUTH_PORTAL_GITEE_ENABLED", "AUTH_OAUTH", "门户 Gitee 登录", 11, "BOOL", "启用", "PORTAL", "GITEE", "FALSE"),
        ("AUTH_OAUTH_PORTAL_GITEE_CLIENT_ID", "AUTH_OAUTH", "门户 Gitee ClientId", 12, "STRING", "Client ID", "PORTAL", "GITEE", ""),
        ("AUTH_OAUTH_PORTAL_GITEE_CLIENT_SECRET", "AUTH_OAUTH", "门户 Gitee ClientSecret", 13, "STRING", "Client Secret", "PORTAL", "GITEE", ""),
        ("AUTH_OAUTH_PORTAL_GITEE_REDIRECT_URI", "AUTH_OAUTH", "门户 Gitee 回调", 14, "STRING", "Redirect URI", "PORTAL", "GITEE", ""),
        ("AUTH_OAUTH_PORTAL_QQ_ENABLED", "AUTH_OAUTH", "门户 QQ 登录", 21, "BOOL", "启用", "PORTAL", "QQ", "FALSE"),
        ("AUTH_OAUTH_PORTAL_QQ_CLIENT_ID", "AUTH_OAUTH", "门户 QQ ClientId", 22, "STRING", "Client ID", "PORTAL", "QQ", ""),
        ("AUTH_OAUTH_PORTAL_QQ_CLIENT_SECRET", "AUTH_OAUTH", "门户 QQ ClientSecret", 23, "STRING", "Client Secret", "PORTAL", "QQ", ""),
        ("AUTH_OAUTH_PORTAL_QQ_REDIRECT_URI", "AUTH_OAUTH", "门户 QQ 回调", 24, "STRING", "Redirect URI", "PORTAL", "QQ", ""),
        ("AUTH_OAUTH_PORTAL_WECHAT_OPEN_ENABLED", "AUTH_OAUTH", "门户微信网页登录", 31, "BOOL", "启用", "PORTAL", "WECHAT_OPEN", "FALSE"),
        ("AUTH_OAUTH_PORTAL_WECHAT_OPEN_CLIENT_ID", "AUTH_OAUTH", "门户微信开放平台 AppId", 32, "STRING", "AppId", "PORTAL", "WECHAT_OPEN", ""),
        ("AUTH_OAUTH_PORTAL_WECHAT_OPEN_CLIENT_SECRET", "AUTH_OAUTH", "门户微信开放平台 Secret", 33, "STRING", "AppSecret", "PORTAL", "WECHAT_OPEN", ""),
        ("AUTH_OAUTH_PORTAL_WECHAT_OPEN_REDIRECT_URI", "AUTH_OAUTH", "门户微信开放平台回调", 34, "STRING", "Redirect URI", "PORTAL", "WECHAT_OPEN", ""),
        ("AUTH_OAUTH_PORTAL_WECHAT_MP_ENABLED", "AUTH_OAUTH", "门户微信小程序登录", 41, "BOOL", "启用", "PORTAL", "WECHAT_MP", "FALSE"),
        ("AUTH_OAUTH_PORTAL_WECHAT_MP_APP_ID", "AUTH_OAUTH", "门户小程序 AppId", 42, "STRING", "AppId", "PORTAL", "WECHAT_MP", ""),
        ("AUTH_OAUTH_PORTAL_WECHAT_MP_APP_SECRET", "AUTH_OAUTH", "门户小程序 AppSecret", 43, "STRING", "AppSecret", "PORTAL", "WECHAT_MP", ""),
        # 管理端 × 提供商（无小程序 UI，仍可配置）
        ("AUTH_OAUTH_ADMIN_GITHUB_ENABLED", "AUTH_OAUTH", "管理端 GitHub 登录", 101, "BOOL", "启用", "ADMIN", "GITHUB", "FALSE"),
        ("AUTH_OAUTH_ADMIN_GITHUB_CLIENT_ID", "AUTH_OAUTH", "管理端 GitHub ClientId", 102, "STRING", "Client ID", "ADMIN", "GITHUB", ""),
        ("AUTH_OAUTH_ADMIN_GITHUB_CLIENT_SECRET", "AUTH_OAUTH", "管理端 GitHub ClientSecret", 103, "STRING", "Client Secret", "ADMIN", "GITHUB", ""),
        ("AUTH_OAUTH_ADMIN_GITHUB_REDIRECT_URI", "AUTH_OAUTH", "管理端 GitHub 回调", 104, "STRING", "Redirect URI", "ADMIN", "GITHUB", ""),
        ("AUTH_OAUTH_ADMIN_GITEE_ENABLED", "AUTH_OAUTH", "管理端 Gitee 登录", 111, "BOOL", "启用", "ADMIN", "GITEE", "FALSE"),
        ("AUTH_OAUTH_ADMIN_GITEE_CLIENT_ID", "AUTH_OAUTH", "管理端 Gitee ClientId", 112, "STRING", "Client ID", "ADMIN", "GITEE", ""),
        ("AUTH_OAUTH_ADMIN_GITEE_CLIENT_SECRET", "AUTH_OAUTH", "管理端 Gitee ClientSecret", 113, "STRING", "Client Secret", "ADMIN", "GITEE", ""),
        ("AUTH_OAUTH_ADMIN_GITEE_REDIRECT_URI", "AUTH_OAUTH", "管理端 Gitee 回调", 114, "STRING", "Redirect URI", "ADMIN", "GITEE", ""),
        ("AUTH_OAUTH_ADMIN_QQ_ENABLED", "AUTH_OAUTH", "管理端 QQ 登录", 121, "BOOL", "启用", "ADMIN", "QQ", "FALSE"),
        ("AUTH_OAUTH_ADMIN_QQ_CLIENT_ID", "AUTH_OAUTH", "管理端 QQ ClientId", 122, "STRING", "Client ID", "ADMIN", "QQ", ""),
        ("AUTH_OAUTH_ADMIN_QQ_CLIENT_SECRET", "AUTH_OAUTH", "管理端 QQ ClientSecret", 123, "STRING", "Client Secret", "ADMIN", "QQ", ""),
        ("AUTH_OAUTH_ADMIN_QQ_REDIRECT_URI", "AUTH_OAUTH", "管理端 QQ 回调", 124, "STRING", "Redirect URI", "ADMIN", "QQ", ""),
        ("AUTH_OAUTH_ADMIN_WECHAT_OPEN_ENABLED", "AUTH_OAUTH", "管理端微信网页登录", 131, "BOOL", "启用", "ADMIN", "WECHAT_OPEN", "FALSE"),
        ("AUTH_OAUTH_ADMIN_WECHAT_OPEN_CLIENT_ID", "AUTH_OAUTH", "管理端微信开放平台 AppId", 132, "STRING", "AppId", "ADMIN", "WECHAT_OPEN", ""),
        ("AUTH_OAUTH_ADMIN_WECHAT_OPEN_CLIENT_SECRET", "AUTH_OAUTH", "管理端微信开放平台 Secret", 133, "STRING", "AppSecret", "ADMIN", "WECHAT_OPEN", ""),
        ("AUTH_OAUTH_ADMIN_WECHAT_OPEN_REDIRECT_URI", "AUTH_OAUTH", "管理端微信开放平台回调", 134, "STRING", "Redirect URI", "ADMIN", "WECHAT_OPEN", ""),
        # 前端回调页
        ("AUTH_OAUTH_FRONTEND_CALLBACK_PORTAL", "AUTH_OAUTH", "门户 OAuth 前端回调页（空则用默认）", 200, "STRING", "门户前端回调", None, None, ""),
        ("AUTH_OAUTH_FRONTEND_CALLBACK_ADMIN", "AUTH_OAUTH", "管理端 OAuth 前端回调页（空则用默认）", 201, "STRING", "管理端前端回调", None, None, ""),
        # 强制绑定与注册通道
        ("AUTH_FORCE_BIND_ADMIN_EMAIL", "AUTH_FORCE_BIND", "管理端强制绑定邮箱", 1, "BOOL", "强制绑定邮箱", "ADMIN", None, "FALSE"),
        ("AUTH_FORCE_BIND_ADMIN_PHONE", "AUTH_FORCE_BIND", "管理端强制绑定手机", 2, "BOOL", "强制绑定手机", "ADMIN", None, "FALSE"),
        ("AUTH_FORCE_BIND_PORTAL_EMAIL", "AUTH_FORCE_BIND", "门户强制绑定邮箱", 3, "BOOL", "强制绑定邮箱", "PORTAL", None, "FALSE"),
        ("AUTH_FORCE_BIND_PORTAL_PHONE", "AUTH_FORCE_BIND", "门户强制绑定手机", 4, "BOOL", "强制绑定手机", "PORTAL", None, "FALSE"),
        ("AUTH_REGISTER_PORTAL_ALLOW_ACCOUNT", "AUTH_REGISTER", "门户用户名注册", 1, "BOOL", "允许用户名注册", "PORTAL", None, "TRUE"),
        ("AUTH_REGISTER_PORTAL_ALLOW_EMAIL", "AUTH_REGISTER", "门户邮箱注册", 2, "BOOL", "允许邮箱注册", "PORTAL", None, "TRUE"),
        ("AUTH_REGISTER_PORTAL_ALLOW_PHONE", "AUTH_REGISTER", "门户手机注册", 3, "BOOL", "允许手机注册", "PORTAL", None, "FALSE"),
    ]
    for row in config_rows:
        _insert_config(op, *row)


def downgrade() -> None:
    op.drop_index("idx_oauth_binding_union", table_name="sys_account_oauth_binding")
    op.drop_index("idx_oauth_binding_account", table_name="sys_account_oauth_binding")
    op.drop_table("sys_account_oauth_binding")
    # 字典与配置种子保持幂等（ON CONFLICT DO NOTHING 风格），降级不删除。


def _insert_dict(op, id_, code, label, value, color, category, parent_id, sort) -> None:
    """插入字典行（不存在时跳过）。"""
    conn = op.get_bind()
    existing = conn.execute(
        sa.text("SELECT 1 FROM sys_dict WHERE id = :id"), {"id": id_}
    ).first()
    if existing:
        return
    conn.execute(
        sa.text(
            "INSERT INTO sys_dict (id, code, label, value, color, category, parent_id, status, sort) "
            "VALUES (:id, :code, :label, :value, :color, :category, :parent_id, 'ENABLED', :sort)"
        ),
        {"id": id_, "code": code, "label": label, "value": value, "color": color, "category": category, "parent_id": parent_id, "sort": sort},
    )


def _insert_config(op, config_key, category, remark, sort, value_type, label, scope, scene, value) -> None:
    """插入配置行（按 config_key 幂等）。"""
    conn = op.get_bind()
    existing = conn.execute(
        sa.text("SELECT 1 FROM sys_config WHERE config_key = :key"), {"key": config_key}
    ).first()
    if existing:
        return
    conn.execute(
        sa.text(
            "INSERT INTO sys_config (id, config_key, config_value, category, remark, sort_code, value_type, label, scope, scene, is_builtin, ext_json) "
            "VALUES (:id, :key, :value, :category, :remark, :sort, :value_type, :label, :scope, :scene, TRUE, :ext_json)"
        ),
        {
            "id": f"cfg_{config_key.lower()}",
            "key": config_key,
            "value": value,
            "category": category,
            "remark": remark,
            "sort": sort,
            "value_type": value_type,
            "label": label,
            "scope": scope,
            "scene": scene,
            "ext_json": "{}",
        },
    )
