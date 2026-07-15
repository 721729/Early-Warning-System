#!/bin/bash
# 绿电哨兵 一键启动
# 用法: bash start.sh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================"
echo "  绿电哨兵 — 一键启动"
echo "========================================"

# ---------- 1. Docker ----------
echo "[1/4] 启动 Docker 数据库..."
docker compose up -d 2>/dev/null

# 等 MySQL 就绪
echo "       等待 MySQL 初始化..."
for i in $(seq 1 30); do
  if docker exec gps-mysql mysqladmin ping -u root -proot123 --silent 2>/dev/null; then
    break
  fi
  sleep 1
done

# 每次启动都运行init.sql (CREATE TABLE IF NOT EXISTS 安全幂等)
echo "       初始化数据库(幂等安全)..."
docker exec -i gps-mysql mysql -u root -proot123 green_power_sentinel < deploy/init.sql 2>/dev/null
echo "       数据库就绪"

echo "       Docker 就绪"

# ---------- 2. 后端 API ----------
echo "[2/4] 启动后端 API (端口 8000)..."
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > /tmp/gps-backend.log 2>&1 &
sleep 2

# 验证后端
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
  echo "       后端启动成功 → http://localhost:8000"
  echo "       API文档 → http://localhost:8000/docs"
else
  echo "       ⚠️  后端可能未就绪, 查看日志: tail -f /tmp/gps-backend.log"
fi

# ---------- 3. 前端 ----------
echo "[3/4] 启动前端 (端口 3000)..."
cd frontend
npm install --silent 2>/dev/null
nohup npm run dev > /tmp/gps-frontend.log 2>&1 &
sleep 3
echo "       前端启动成功 → http://localhost:3000"

# ---------- 4. 完成 ----------
echo "[4/4] 全部就绪!"
echo ""
echo "  浏览器打开: http://localhost:3000"
echo "  账号: admin"
echo "  密码: admin123"
echo ""
echo "  停止服务: bash stop.sh"
