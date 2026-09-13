# 数据库迁移

Alembic 版本目录，只管理**表结构**增量变更。

- **PostgreSQL 演示全量**（含种子）：[`scripts/db.sql`](../scripts/db.sql)
- **MySQL / 可移植建表**：对本空库执行 `alembic upgrade head`（种子数据需另行导入或走业务初始化）

```bash
# 在项目根目录执行；DB__URL 支持 postgresql+asyncpg / mysql+aiomysql（或 asyncmy）
alembic upgrade head
alembic revision --autogenerate -m "describe schema change"
alembic check
```

连接串来自 `.env` 的 `DB__URL`（见 `alembic.ini` / `migrations/env.py`）。

> 应用启动（`entrypoint.sh`）不会执行迁移；以上命令仅在维护机手动执行。
