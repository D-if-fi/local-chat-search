#!/bin/bash
# macOS 双击启动：在 Finder 里双击本文件即可（首次可能需要在「系统设置 → 隐私与安全性」里放行）
cd "$(dirname "$0")" || exit 1
export CHAT_SEARCH_KEEP_OPEN=1
exec bash ./start.sh "$@"
