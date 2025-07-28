import os

# 获取环境变量中的端口，默认为 8000
port = int(os.environ.get('PORT', 8000))

# Gunicorn 配置
bind = f"0.0.0.0:{port}"
workers = 1
worker_class = "sync"
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 100 