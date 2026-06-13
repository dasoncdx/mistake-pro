#!/bin/bash
set -e
echo "=== 错题Pro 启动 ==="
echo "Python: $(python --version)"
echo "PORT: ${PORT:-8080}"
echo "=== 安装依赖 ==="
pip install -r requirements.txt -q
echo "=== 启动服务 ==="
exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8080}" --log-level info
