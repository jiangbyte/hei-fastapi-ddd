# hei-fastapi-ddd

基于 **DDD（领域驱动设计）** 的 FastAPI 工程。与 [hei-fastapi](../hei-fastapi) **对外契约一致**（`/api/v1/admin|portal/**`、`ApiResponse`、Cookie/Session、权限码、库表），业务能力对等；对内按限界上下文 + 四层架构全面重建。

## 工程目录

```text
hei-fastapi-ddd/
├── pyproject.toml / alembic.ini / migrations / scripts / docker
├── tests/{api,unit,domain}
└── src/hei_fastapi_ddd/
    ├── main.py / factory.py / lifespan.py / routers.py / db_models.py
    ├── ddd_kernel/          # AggregateRoot、DomainEvent、Repository Protocol…
    ├── shared/              # web / persistence / redis / security / messaging…
    └── contexts/            # auth | iam | sys | profile | biz
        └── <bc>/
            ├── domain/           # 聚合、值对象、领域事件、仓储接口
            ├── application/      # 用例服务；application/api 为跨上下文端口
            ├── infrastructure/   # ORM PO、仓储实现、出站适配
            └── interfaces/http/  # FastAPI 路由与 Schema（路径契约冻结）
```

依赖方向：`interfaces → application → domain`；`infrastructure → domain`；跨上下文只依赖对方 `application.api` 或进程内事件。

## 契约与运行

- 默认库/种子与 `hei-fastapi` 同源（`scripts/hei_fastapi.sql`、Alembic migrations）。
- 前端 `hei-admin` / `hei-portal` 切换后端地址即可对接。
- ASGI：`hei_fastapi_ddd.main:app`

```bash
cd hei-fastapi-ddd
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,mysql]"   # 或 postgres
cp .env.example .env            # 配置 DB__URL / REDIS__URL
uvicorn hei_fastapi_ddd.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
pytest tests/domain tests/api/test_health.py -q
```

## 与 hei-fastapi 的关系

| | hei-fastapi | hei-fastapi-ddd |
|--|-------------|-----------------|
| 对外 API / 表结构 | 基准契约 | **保持一致** |
| 代码组织 | `modules/*/service` 事务脚本 | 限界上下文四层 + 聚合 |
| 跨模块协作 | 直连 Repository/Service | 端口 / 领域与集成事件 |

现有 `hei-fastapi` **不修改**；本仓库为并行重建项目。

## License

Apache License 2.0（见 `LICENSE`）。
