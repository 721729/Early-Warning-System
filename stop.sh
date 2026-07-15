#!/bin/bash
echo "停止全部服务..."
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "  后端已停止"
lsof -ti:3000 | xargs kill -9 2>/dev/null && echo "  前端已停止"
docker compose down 2>/dev/null && echo "  Docker已停止"
echo "完成"
