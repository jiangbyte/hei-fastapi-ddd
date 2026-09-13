# Build from repo root (no docker compose; same style as hei-boot / hei-fastapi):
#   docker build -t hei-fastapi-ddd .
#   docker run -d --name hei-ddd -p 8000:8000 \
#     -e APP__CONFIG_CRYPTO_KEY=... -e DB__URL=... -e REDIS__URL=... \
#     -v hei_storage:/app/storage hei-fastapi-ddd
#
# 生产必填环境变量见 README。
# 容器只启动 API，不执行数据库迁移（表结构由人工维护）。
#FROM python:3.11-slim
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim
#FROM docker.xuanyuan.run/library/python:3.11-slim

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security hardening.
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --home-dir /app --shell /usr/sbin/nologin appuser

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP__HOST=0.0.0.0 \
    APP__PORT=8000 \
    APP__DEBUG=false \
    DB__POOL_SIZE=5 \
    DB__MAX_OVERFLOW=5 \
    DB__POOL_PRE_PING=true \
    DB__POOL_RECYCLE_SECONDS=1800 \
    AUDIT__OPERATION_QUEUE_SIZE=1000 \
    AUDIT__OPERATION_SHUTDOWN_TIMEOUT_SECONDS=5

ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
COPY pyproject.toml ./
COPY README.md ./
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" --prefer-binary -r requirements.txt \
    && python -m pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" --no-deps -e .

COPY alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY gunicorn.conf.py ./
COPY entrypoint.sh ./

RUN chmod +x entrypoint.sh && mkdir -p /app/storage /app/.runtime/storage

RUN chown -R appuser:appgroup /app/storage /app/.runtime
USER appuser

VOLUME ["/app/storage", "/app/.runtime"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)"]

ENTRYPOINT ["tini", "-g", "--", "/app/entrypoint.sh"]
