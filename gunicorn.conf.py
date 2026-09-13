# 脚手架阶段不依赖 settings；Phase 1 接入配置后可改回动态 bind。
bind = "0.0.0.0:8000"
worker_class = "uvicorn.workers.UvicornWorker"
# 多 worker 各自运行内置任务调度器；同一任务的执行由 Redis 锁串行化，
# 保证不会重复执行（对齐 hei-boot / hei-fastapi 调度模型）。
max_requests = 10000
max_requests_jitter = 1000
timeout = 30
graceful_timeout = 30
keepalive = 5
accesslog = None
errorlog = "-"
loglevel = "info"
