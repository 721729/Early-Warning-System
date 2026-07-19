#!/bin/bash
# 绿电哨兵 一键启动
#   智能环境检测：缺 Docker / Python / Node 自动提示安装并询问
#   一键启动仿真引擎 + 后端 + 前端 + 阈值自动重算
# 用法: bash start.sh
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 子模块初始化 (审核克隆可能没用 --recurse-submodules)
if [ ! -f ml/PatchTST/README.md ]; then
  echo "⚡ 初始化 PatchTST 子模块..."
  git submodule update --init --recursive 2>/dev/null || echo "   (跳过, 将使用简易模式运行)"
fi

echo "========================================"
echo "  绿电哨兵 — 一键启动"
echo "========================================"

# ---------- 0. 环境检查 ----------
echo "[0/4] 检查运行环境..."
MISSING=""

# 检查 Docker
if ! command -v docker &>/dev/null; then
  MISSING="$MISSING docker"
fi

# 检查 Python 3.10+
PY_OK=$(python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null && echo "yes" || echo "no")
if [ "$PY_OK" != "yes" ]; then
  MISSING="$MISSING python3.10+"
fi

# 检查 python3-venv (创建虚拟环境必需)
python3 -m venv --help >/dev/null 2>&1 || MISSING="$MISSING python3-venv"

# 检查 Node.js 18+
NODE_OK=$(node -e "process.exit(parseInt(process.version.slice(1)) >= 18 ? 0 : 1)" 2>/dev/null && echo "yes" || echo "no")
if [ "$NODE_OK" != "yes" ]; then
  MISSING="$MISSING node18+"
fi

if [ -n "$MISSING" ]; then
  echo "       缺少: $MISSING"
  echo ""
  echo "   Ubuntu/Debian 安装命令:"
  for m in $MISSING; do
    case $m in
      docker)    echo "     sudo apt install docker.io && sudo systemctl start docker" ;;
      python3.10+) echo "     sudo apt install python3 python3-pip python3-venv" ;;
      node18+)   echo "     curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install nodejs" ;;
    esac
  done
  echo ""
  read -p "  是否自动安装? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo apt update -qq
    for m in $MISSING; do
      case $m in
        docker)    sudo apt install -y docker.io && sudo systemctl start docker ;;
        python3.10+) sudo apt install -y python3 python3-pip python3-venv ;;
        python3-venv) sudo apt install -y python3-venv ;;
        node18+)   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs ;;
      esac
    done
  else
    echo "       请手动安装后再运行 start.sh"; exit 1
  fi
fi
echo "       环境就绪 (Docker $(docker --version 2>/dev/null | cut -d' ' -f3 | cut -d'.' -f1), Python $(python3 --version 2>/dev/null | cut -d' ' -f2), Node $(node --version 2>/dev/null | cut -d'v' -f2))"

# ---------- 1. Docker ----------
echo "[1/4] 启动 Docker 数据库..."
# SEC-003: 口令统一来自 .env, compose 与本脚本均不再内置弱默认值
if [ ! -f .env ]; then
  echo "✗ 缺少 .env —— 请先执行: cp .env.example .env 并修改其中的 CHANGE_ME 强口令"
  exit 1
fi
set -a; source .env; set +a
docker compose up -d 2>/dev/null || echo "       Docker未启动"

# 等 MySQL 就绪
echo "       等待 MySQL 初始化..."
for i in $(seq 1 30); do
  if docker exec gps-mysql mysqladmin ping -u root -p"$MYSQL_ROOT_PASS" --silent 2>/dev/null; then
    break
  fi
  sleep 1
done

# 每次启动都运行init.sql (CREATE TABLE IF NOT EXISTS 安全幂等)
echo "       初始化数据库(幂等安全)..."
docker exec -i gps-mysql mysql -u root -p"$MYSQL_ROOT_PASS" green_power_sentinel < deploy/init.sql 2>/dev/null
echo "       数据库就绪"

echo "       Docker 就绪"

# ---------- 2. 后端 API ----------
echo "[2/4] 启动后端 API (端口 8000)..."
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
else
  python3 -m venv .venv && source .venv/bin/activate
fi
pip install -q -r backend/requirements.txt -r ml/requirements.txt 2>/dev/null
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
