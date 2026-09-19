#!/bin/sh
set -eu

# 仅启动 API（内置任务调度器随应用进程运行，任务定义在 sys_job 表）。
# 数据库表结构由人工维护：应用启动不执行迁移/种子。
exec gunicorn hei_fastapi_ddd.app.main:app -c gunicorn.conf.py
