# HEI FastAPI DDD

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116%2B-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2%20Async-D71F00?logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supported-4169E1?logo=postgresql&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Supported-4479A1?logo=mysql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Supported-DC382D?logo=redis&logoColor=white)
![License](https://img.shields.io/badge/License-Apache_2.0-blue)
![Version](https://img.shields.io/badge/version-1.1.0--beta-orange)

**HEI FastAPI DDD** 是 [hei-fastapi](https://github.com/jiangbyte/hei-fastapi) 的 **DDD 重建版**：对外 API、响应信封、会话 Cookie、权限码与库表契约保持一致，对内按限界上下文 + **常见六层工程模型**组织，便于长期演进与测试。

> 当前版本：`1.1.0-beta` · 协议：[Apache License 2.0](LICENSE) · 姊妹基准：[hei-fastapi](https://github.com/jiangbyte/hei-fastapi)

## 目录

- [功能特性](#功能特性)
- [与 hei-fastapi 的关系](#与-hei-fastapi-的关系)
- [前端姊妹项目](#前端姊妹项目)
- [技术栈](#技术栈)
- [工程结构](#工程结构)
- [快速开始](#快速开始)
- [默认账号](#默认账号)
- [姊妹项目](#姊妹项目)
- [License](#license)

## 功能特性

API 前缀仍为 `/api/v1/admin/*` 与 `/api/v1/portal/*`，业务能力与 `hei-fastapi` 对等：

| 模块 | 说明 |
| --- | --- |
| 双端账号体系 | ADMIN / PORTAL 独立会话（HttpOnly Cookie / Authorization）；密码 RSA 传输、验证码登录、失败锁定与限流；OAuth |
| RBAC 权限 | 账号 / 角色 / 部门 / 用户组 / 岗位；菜单、按钮与 API 授权；在线会话踢出（领域/集成事件驱动） |
| 系统管理 | 字典、动态配置（Fernet）、Banner、公告 / 通知、意见反馈、弱口令库 |
| 对象存储 | S3 兼容（MinIO / RustFS / OSS / COS），直链或预签名 |
| 运维能力 | 操作审计与告警、登录日志、工作台、内置任务调度（`sys_job`） |
| 代码生成 | 单表 / 树表 / 主子表方案，预览与 ZIP |
| 实名认证 | 工单提交与审核、敏感字段加密 |
| 业务扩展 | `contexts/biz` 示例限界上下文，可按同样六层横向扩展 |

## 与 hei-fastapi 的关系

| | hei-fastapi | hei-fastapi-ddd（本仓库） |
| --- | --- | --- |
| 对外 API / 表结构 / 种子 | 基准契约 | **保持一致**（可切换后端地址对接同一前端） |
| 代码组织 | `app/modules/*/service` 事务脚本 | 限界上下文内六层：`api / trigger / domain / application / infrastructure`（外加顶层 `types` / `app`） |
| 跨模块协作 | 直连 Repository / Service | 应用端口、领域事件 / 集成事件 |
| 仓库定位 | 现网基准实现 | **并行重建**，不原地改写 `hei-fastapi` |

ASGI 入口：`hei_fastapi_ddd.app.main:app`（对应旧版 `app.main:app`）。

## 前端姊妹项目

| 项目 | 说明 |
| --- | --- |
| [**hei-admin**](https://github.com/jiangbyte/hei-admin) | Vue 3 管理端，对接 `/api/v1/admin/*` |
| [**hei-portal**](https://github.com/jiangbyte/hei-portal) | React 门户，对接 `/api/v1/portal/*` |
| [**hei-admin-uniapp**](https://github.com/jiangbyte/hei-admin-uniapp) | uni-app 管理端移动端 |

将前端代理目标指向本服务端口即可（默认示例 `8000`）。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11+ · FastAPI · uvicorn / gunicorn · Pydantic Settings |
| 持久化 | PostgreSQL / MySQL · SQLAlchemy 2（async）· Alembic · asyncpg / aiomysql |
| 缓存 / 会话 | Redis |
| 架构 | `ddd_kernel`（AggregateRoot / DomainEvent / Repository…）· 进程内 messaging |
| 文档 | OpenAPI（`/docs`、`/redoc`，默认关闭，见 `.env.example`） |
| 其他 | boto3 / oss2 · croniter · cryptography · OpenTelemetry（可选） |

## 工程结构

```text
hei-fastapi-ddd/
├── src/hei_fastapi_ddd/
│   ├── app/                     # 启动层：main / factory / lifespan / routers
│   ├── types/                   # 跨层异常类型
│   ├── ddd_kernel/              # 聚合、事件、仓储协议等内核抽象
│   ├── shared/                  # web / persistence / redis / security / messaging…
│   └── contexts/                # auth | iam | sys | profile | biz
│       └── <bc>/
│           ├── api/             # HTTP Schema（契约 DTO）
│           ├── trigger/http/    # FastAPI 路由
│           ├── domain/          # 聚合、值对象、领域事件、仓储接口
│           ├── application/     # 用例编排（归属 domain 层职责）；application/api 为跨上下文端口
│           └── infrastructure/  # ORM PO、仓储实现、出站适配
├── scripts/hei_fastapi.sql      # MySQL 建表 + 种子（与 hei-fastapi 同源）
├── migrations/                  # Alembic 增量
└── tests/                       # domain / api / unit
```

依赖方向（严格，不可反向）：

```text
trigger → api / application
application → domain（仓储 Protocol）／跨 BC 仅经 application.api 端口
infrastructure → domain（实现 Protocol）
app → trigger / infrastructure（装配）
```

- application / infrastructure **禁止** import `trigger`
- application **禁止** import 本 BC 或他 BC 的 `infrastructure` / `api` Schema
- infrastructure **禁止** import `api` Schema（HTTP 契约只在 trigger 边界转换）
- 跨 BC 禁止直连对方 `infrastructure`；`shared/` 视为平台能力可依赖

代码生成按六层路径产出：`api/` Schema、`trigger/http` router、`application`（DTO + Protocol 注入）、`domain` repository、`infrastructure` Impl + wiring；不再生成 `interfaces` 或 application 内 `Repository(db)`。

`scripts/` 与 `migrations/`：

| 文件 / 目录 | 用途 |
| --- | --- |
| `scripts/hei_fastapi.sql` | MySQL 建表+种子（无 DROP；`IF NOT EXISTS` / `INSERT IGNORE`） |
| `migrations/` | Alembic 增量表结构（PG / MySQL，见 [`migrations/README.md`](migrations/README.md)） |

## 快速开始

### 环境要求

- Python **3.11+**
- MySQL 8+（演示种子）、Redis
- PostgreSQL 亦可（Alembic 建表，见 `migrations/README.md`）

### 1. 初始化数据库

**MySQL 8+（本地演示，含种子，推荐）：**

```bash
mysql -u root -p -e "CREATE DATABASE hei_fastapi DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p hei_fastapi < scripts/hei_fastapi.sql
```

`scripts/hei_fastapi.sql` **不含 `DROP TABLE`**，重复导入**不会清空**已有库。

与 `hei_boot` / `hei-fastapi` 表结构对齐；`sys_job.handler` 使用 FastAPI 栈标识（如 `sys_job_sample`）。

**Alembic（可移植建表）：**

```bash
cp .env.example .env
# DB__URL=mysql+aiomysql://root:123456@127.0.0.1:3306/hei_fastapi?charset=utf8mb4

pip install -e ".[dev,mysql]"   # 或 ".[dev,postgres]"
alembic upgrade head
```

配置见 [`.env.example`](.env.example)。`APP__CONFIG_CRYPTO_KEY` 须与种子中 `sys_config` 密文匹配；生产请更换 Fernet 密钥。

> 应用启动（`entrypoint.sh`）不执行迁移；`alembic upgrade head` 仅在维护时手动执行。

### 2. 启动后端

```bash
pip install -e ".[dev,mysql]"
cp .env.example .env
# 按需修改 DB__URL / REDIS__URL 等
python -m uvicorn hei_fastapi_ddd.app.main:app --host 127.0.0.1 --port 8000 --reload
```

| 项 | 地址 |
| --- | --- |
| API | http://127.0.0.1:8000 |
| OpenAPI | http://127.0.0.1:8000/docs（需 `SWAGGER__ENABLED=true`） |
| ReDoc | http://127.0.0.1:8000/redoc（需 `SWAGGER__ENABLED=true`） |

> Linux / 容器可用 `./entrypoint.sh`（gunicorn）。Docker 见 [`docker/`](docker/) 与 [`Dockerfile`](Dockerfile)。

### 3. 启动前端（可选）

前端为独立仓库，默认将 `/api` 代理到 `http://127.0.0.1:8000`：

```bash
git clone https://github.com/jiangbyte/hei-admin.git && cd hei-admin
pnpm install && pnpm dev

git clone https://github.com/jiangbyte/hei-portal.git && cd hei-portal
pnpm install && pnpm dev
```

### 4. 测试

```bash
pytest tests/domain tests/api tests/unit -q
```

## 默认账号

| 端 | 前端仓库 | 地址 | 账号 | 密码 | 说明 |
| --- | --- | --- | --- | --- | --- |
| Admin | [hei-admin](https://github.com/jiangbyte/hei-admin) | http://127.0.0.1:5173 | `superadmin` | `123456` | 超级管理员（`*:*:*`） |

> 仅供本地演示。部署后请修改默认密码，并更换配置加密密钥、对象存储凭证等。更多种子见 `scripts/hei_fastapi.sql`。

## 姊妹项目

| 项目 | 说明 | 协议 |
| --- | --- | --- |
| [**hei-fastapi**](https://github.com/jiangbyte/hei-fastapi) | FastAPI 基准实现（契约来源） | Apache License 2.0 |
| [**hei-boot**](https://github.com/jiangbyte/hei-boot) | Spring Boot 脚手架 | Apache License 2.0 |
| [**hei-gin**](https://github.com/jiangbyte/hei-gin) | Go / Gin 后端 | Apache License 2.0 |
| [**hei-ddd-lite**](https://github.com/jiangbyte/hei-ddd-lite) | Java DDD 单体模板 | Apache License 2.0 |
| [**hei-admin**](https://github.com/jiangbyte/hei-admin) | Vue 3 管理端前端 | Apache License 2.0 |
| [**hei-portal**](https://github.com/jiangbyte/hei-portal) | React 门户前端 | Apache License 2.0 |
| [**hei-admin-uniapp**](https://github.com/jiangbyte/hei-admin-uniapp) | uni-app 管理端移动端 | Apache License 2.0 |

## License

本项目基于 [Apache License 2.0](LICENSE) 开源。完整条款见 [LICENSE](LICENSE)，版权声明见 [NOTICE](NOTICE).
