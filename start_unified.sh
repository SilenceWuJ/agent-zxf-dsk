#!/bin/bash
# =====================================================
# 统一入口启动脚本 — Plan A (反向代理 + 统一门户)
# 同时启动:
#   1. Node.js 后端 (端口 3001) — Word 文档填充工具
#   2. Flask 后端 (端口 5004) — AI张老师 + 反向代理
# =====================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
THIRD_V_DIR="/Users/xixi/third_v"

echo "====================================="
echo "  启动统一入口服务"
echo "====================================="

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ---------- 1. Node.js 后端 ----------
echo ""
echo -e "${YELLOW}[1/3] 启动 Word 文档填充服务 (Node.js :3001)...${NC}"

cd "$THIRD_V_DIR/backend"

# 检查是否已运行
if lsof -i :3001 -P -n 2>/dev/null | grep LISTEN > /dev/null; then
    echo -e "${GREEN}  ✓ 端口 3001 已被占用 (可能已启动)，跳过${NC}"
else
    npm start &
    NODE_PID=$!
    echo -e "${GREEN}  ✓ Node.js 服务已启动 (PID: $NODE_PID)${NC}"
    # 等待服务就绪
    sleep 2
fi

# ---------- 2. 数据库检查 ----------
echo ""
echo -e "${YELLOW}[2/3] 检查数据库...${NC}"

cd "$SCRIPT_DIR"

# 开发环境：检查是否需要重建数据库（含新表 verification_codes）
if [ -f "app.db" ]; then
    # 检查是否包含新表
    HAS_NEW_TABLE=$(python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='verification_codes'\")
    result = c.fetchone()
    conn.close()
    print('yes' if result else 'no')
except:
    print('no')
")
    if [ "$HAS_NEW_TABLE" = "no" ]; then
        echo -e "${YELLOW}  数据库需要升级，删除旧库并重建...${NC}"
        rm -f app.db
        echo -e "${GREEN}  ✓ 已删除旧数据库，启动时将自动重建${NC}"
    else
        echo -e "${GREEN}  ✓ 数据库已是最新${NC}"
    fi
else
    echo -e "${GREEN}  ✓ 将创建新的数据库${NC}"
fi

# ---------- 3. Flask 后端 ----------
echo ""
echo -e "${YELLOW}[3/3] 启动 AI张老师 统一门户 (Flask :5004)...${NC}"

cd "$SCRIPT_DIR"

if lsof -i :5004 -P -n 2>/dev/null | grep LISTEN > /dev/null; then
    echo -e "${GREEN}  ✓ 端口 5004 已被占用 (可能已启动)，跳过${NC}"
else
    python3 app.py &
    FLASK_PID=$!
    echo -e "${GREEN}  ✓ Flask 服务已启动 (PID: $FLASK_PID)${NC}"
    sleep 2
fi

# ---------- 4. 检查状态 ----------
echo ""
echo "====================================="
echo -e "  ${GREEN}统一入口服务启动完成!${NC}"
echo "====================================="
echo ""
echo -e "  Flask (AI张老师):   ${GREEN}http://localhost:5004${NC}"
echo -e "  登录页面:           ${GREEN}http://localhost:5004/login${NC}"
echo -e "  Word 工具 (代理):   ${GREEN}http://localhost:5004/word/${NC}"
echo -e "  Node.js (直连):     ${GREEN}http://localhost:3001${NC}"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "====================================="

# 等待任意子进程退出
wait
