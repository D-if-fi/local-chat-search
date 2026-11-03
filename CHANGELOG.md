# 更新日志

## v2.1.0 — 跨平台一键启动与英文文档

- 启动脚本统一为 `start.sh`（macOS/Linux）、`start.command`（macOS 双击）、`start.bat`（Windows cmd）、`start.ps1`（Windows PowerShell），自动探测 `py -3` / `python3` / `python`
- 端口可传参（`./start.sh 8888`、`start.bat 8888`、`--port`、`CHAT_SEARCH_PORT`）；端口被占用时自动向后顺延并打印实际端口
- 首页改版：本地运行徽标、整页拖拽遮罩、Toast 提示、键盘快捷键（`/` `⌘K` `↑` `↓` `Enter` `Esc`）、点击消息复制、窄屏单栏浮层、清空数据库二次确认
- 新增 `/api/health` 健康检查接口；`/api/import/reset` 必须带 `confirm=1` 才能清库
- 启动横幅打印版本、平台、Python 版本与数据目录
- 文档：`README.md` 改为英文为主，中文版移至 `README.zh-CN.md`，新增各平台启动方式对照表；补充 `docs/screenshot.png`
- CI 增加启动脚本语法检查（bash / PowerShell 解析）

## v2.0.0 — 支持任意来源的聊天记录

- 新增多格式适配：通用 JSON / JSONL、纯文本（行首时间戳 + 续行合并）
- 单文件（非 zip）可直接拖入导入，不再要求必须打包
- 新增 `tools/csv_to_jsonl.py`，CSV 先转 JSONL 再导入
- 新增 `CHAT_SEARCH_DATA` 环境变量，可指定数据库位置（便于隔离测试与多库切换）
- 修复：单文件导入时用临时文件名当会话名的问题
- 修复：不同单文件因同名被并成同一个会话桶的问题
- 新增端到端冒烟测试 `tests/smoke_test.py` 与 GitHub Actions CI
- 修复：Windows 上 stdout 非 UTF-8 导致启动横幅 `UnicodeEncodeError`，服务直接退出
- 新增 `CHAT_SEARCH_NO_BROWSER=1`，脚本/CI 场景下跳过自动打开浏览器

## v1.0.0 — 首个可用版本

- 飞书聊天记录导出包（zip）导入：会话名、发送人、消息类型、撤回状态
- SQLite + FTS5 自建 bigram 索引，两字中文词毫秒级检索
- 单字查询回退 `LIKE` 全表扫描
- 按会话 / 发送人 / 日期范围 / 消息类型筛选，命中上下文面板
- 本地 HTTP 服务只绑 `127.0.0.1`，零第三方依赖
- macOS / Windows 双击启动脚本
