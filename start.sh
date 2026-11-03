#!/usr/bin/env bash
# local-chat-search - macOS / Linux 一键启动
# 用法: ./start.sh [port]    默认端口 8777，被占用时服务端自动顺延
set -u

cd "$(dirname "$0")" || exit 1

PORT="${1:-${CHAT_SEARCH_PORT:-8777}}"

PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
      PY="$cand"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  cat <<'EOF'
未找到 Python 3.8 或更高版本。

  macOS:  brew install python3
          或到 https://www.python.org/downloads/ 下载安装
  Linux:  sudo apt install python3   (Debian/Ubuntu)
          sudo dnf install python3   (Fedora/RHEL)
EOF
  exit 1
fi

PYVERSION="$("$PY" -V 2>&1)"
echo "解释器: $PY ($PYVERSION)"
echo "端口: $PORT"
echo

"$PY" app/server.py --port "$PORT"
status=$?

# 双击启动时让终端窗口保持打开，方便看清报错
if [ "${CHAT_SEARCH_KEEP_OPEN:-0}" != "0" ] && [ -t 0 ]; then
  printf '\n服务已停止 (退出码 %s)，按回车关闭窗口…' "$status"
  read -r _ || true
fi

exit "$status"
