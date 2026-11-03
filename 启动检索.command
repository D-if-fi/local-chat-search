#!/bin/bash
# macOS / Linux 启动脚本：双击即可运行
cd "$(dirname "$0")" || exit 1

PORT=8777

PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c "import sqlite3,sys;sys.exit(0 if sys.version_info>=(3,8) else 1)" >/dev/null 2>&1; then
      PY="$cand"; break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "未检测到 Python 3.8 或更高版本。"
  echo "请先安装 Python：https://www.python.org/downloads/"
  echo ""
  read -n 1 -s -r -p "按任意键退出…"
  exit 1
fi

echo "正在启动聊天记录检索…"
"$PY" app/server.py "$PORT"
echo ""
read -n 1 -s -r -p "服务已停止，按任意键关闭窗口…"
