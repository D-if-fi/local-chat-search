# local-chat-search

[![CI](https://github.com/D-if-fi/local-chat-search/actions/workflows/ci.yml/badge.svg)](https://github.com/D-if-fi/local-chat-search/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)](#快速开始)

把自己导出的聊天记录变成**离线、可全文检索、数据不出本机**的本地资料库。

零第三方依赖（只用 Python 标准库），一条命令或双击脚本即可启动；数据只写在 `data/chat_search.db`，服务只监听 `127.0.0.1`，不联网、不上传、不需要账号。

[English](README.md) | 简体中文

> **只想用、不想折腾？** 不用装 Python，直接下载双击：
> [macOS 版](downloads/local-chat-search-macos.zip) · [Windows 版](downloads/local-chat-search-windows.exe)

![界面截图](docs/screenshot.png)

## 为什么做这个

聊天记录导出包通常是几百个 JSON 文件堆在一个 zip 里，想找「上次那个割接窗口怎么定的」只能靠翻。上传到任何在线工具，又等于把自己几年的对话交给第三方。

这个项目只做一件事：**在本机把导出包变成一个能搜的库**，并配一个干净的搜索页。

- 83 万条消息实测：导入约 1~1.5 分钟，检索毫秒级
- 单进程、无依赖、无服务端、无账号、无遥测
- 多格式兼容：任何来源的聊天记录，只要有时间/发送人/内容字段就能进来

## 下载直接用（不装 Python、不开终端）

非技术用户看这里：到 [**Releases**](https://github.com/D-if-fi/local-chat-search/releases/latest) 下载打包好的可执行文件，双击即用，不需要装任何环境。

| 平台 | 下载文件 | 怎么用 |
| --- | --- | --- |
| macOS | `local-chat-search-macos.zip` | 解压 → 双击 `local-chat-search.app` |
| Windows | `local-chat-search-windows.exe` | 双击这个 `.exe` |

程序会自己起本地服务并打开搜索页面，没有黑窗口、不用敲命令。

程序**未做代码签名**，所以第一次打开需要多一步：

- **macOS** 提示「Apple 无法验证」：右键点 App → **打开** → 再点 **打开**（或到 系统设置 → 隐私与安全性 → **仍要打开**）
- **Windows** 提示「Windows 已保护你的电脑」：点 **更多信息** → **仍要运行**

数据存放位置：

| | 默认位置 | 便携模式（数据跟着程序走） |
| --- | --- | --- |
| macOS | `~/Library/Application Support/local-chat-search/data` | 在 `.app` 同级建一个 `data/` 文件夹 |
| Windows | `%LOCALAPPDATA%\local-chat-search\data` | 在 `.exe` 同级建一个 `data/` 文件夹 |

关闭程序即停止服务（macOS：Control + 点 Dock 图标 → 退出；Windows：关掉弹出的控制台窗口）。

## 从源码运行

需要 **Python 3.8+**（macOS / Windows / Linux 均可），不需要 `pip install` 任何东西。

### 方式一 · 一键脚本

| 平台 | 双击 | 或在终端执行 |
| --- | --- | --- |
| macOS | `start.command` | `./start.sh` |
| Windows | `start.bat` | `start.bat 8888` |
| Windows（PowerShell） | 右键 → 使用 PowerShell 运行 | `powershell -ExecutionPolicy Bypass -File .\start.ps1` |
| Linux | — | `./start.sh` |

三个脚本都会自动寻找已安装的 Python 3.8+，启动服务并打开 `http://127.0.0.1:8777`。

### 方式二 · 命令行

```bash
git clone https://github.com/D-if-fi/local-chat-search.git
cd local-chat-search
python3 app/server.py            # http://127.0.0.1:8777
```

### 常用参数

| 需求 | 做法 |
| --- | --- |
| 换端口 | `./start.sh 8888` · `start.bat 8888` · `python3 app/server.py --port 8888` |
| 端口被占用 | 服务自动从 8777 向后顺延（最多 10 个），并打印实际端口 |
| 换数据目录 | `CHAT_SEARCH_DATA=~/my-chat-db python3 app/server.py`（Windows 设同名环境变量） |
| 不自动开浏览器 | `CHAT_SEARCH_NO_BROWSER=1 python3 app/server.py` |
| 健康检查 | `curl http://127.0.0.1:8777/api/health` |

首次打开页面会弹导入向导，把导出包拖进去即可，导入在后台进行。之后任何时候都能把文件拖到页面上追加。

> macOS 首次双击 `start.command` 若提示「无法打开」，右键 → 打开，或执行一次 `chmod +x start.command start.sh`。

## 自己构建可执行文件

Release 里的成品由 GitHub Actions 在打 `v*` tag 时自动构建（`.github/workflows/release.yml`）。本地构建：

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install pyinstaller
python tools/build_app.py
```

产物在 `build/dist/`：macOS 是 `local-chat-search.app`，Windows 是 `local-chat-search.exe`。PyInstaller 只是打包工具，程序本身运行时依然只用标准库。

## 支持的输入

| 输入 | 说明 |
| --- | --- |
| 飞书 / Lark 聊天记录导出包 | zip 内含 `chats/*.json` + `chat_list.json`，自动识别会话名、发送人、消息类型与撤回状态 |
| 通用 JSON / JSONL | 自动识别常见字段名（见下表）；单文件或打包成 zip 均可 |
| 纯文本 | 行首带时间戳的 txt，如 `[2024-03-02 09:00:12] 张三: 内容`；缩进续行自动并入上一条 |
| CSV | 先用 `tools/csv_to_jsonl.py` 转成 JSONL，再导入 |

字段名不用改，会自动匹配（大小写、下划线、空格不敏感）：

| 用途 | 可识别的字段名 |
| --- | --- |
| 时间 | `time` `create_time` `timestamp` `ts` `date` `datetime`（秒/毫秒时间戳或日期字符串都行） |
| 发送人 | `sender` `from` `name` `username` `author` |
| 内容 | `content` `text` `message` `msg` `body` |
| 会话 | `chat_name` `chat` `group` `title` `conversation` `room` |

重复导入同一份包**不会**产生重复数据（按稳定消息 ID 去重），每次导出新记录后直接再拖进去即可增量合并。

`examples/` 里三种格式各有一份样例，可以直接拿来跑通流程。

## 搜索能力

- 关键词全文检索，空格分隔多个词 = 同时包含
- 双引号包住按整体短语匹配，如 `"带宽 割接"`
- 按会话、发送人、日期范围、消息类型筛选，可只查已撤回消息
- 点结果查看该条消息前后各 12 条原始上下文

快捷键：`/` 或 `⌘K` 聚焦搜索框，`↑`/`↓` 切换结果，`Enter` 打开，`Esc` 关闭面板；点击消息即可复制原文。

## 隐私

- 数据只写在 `data/chat_search.db`，删掉即回到初始状态
- 服务只绑 `127.0.0.1`，同局域网其它设备也访问不到
- 仓库 `.gitignore` 已排除 `data/`、`*.db`，CI 会检查误提交
- 图片、语音、视频、表情在源数据里没有文字，只能检索到占位标记，不做 OCR

## 目录结构

```
local-chat-search/
├── app/
│   ├── server.py         本地 HTTP 服务 + SQLite 检索（标准库）
│   ├── importer.py       导出包解析与多格式适配
│   └── index.html        单页检索界面
├── tools/csv_to_jsonl.py CSV → JSONL 转换
├── examples/             三种格式的样例数据
├── tests/smoke_test.py   端到端冒烟测试
├── docs/ARCHITECTURE.md  实现说明：表结构、索引策略、检索路由
├── start.command         macOS 双击启动
├── start.sh              macOS / Linux 启动
├── start.bat             Windows 启动（cmd）
└── start.ps1             Windows 启动（PowerShell）
```

## 开发

```bash
python3 tests/smoke_test.py   # 起服务→导入 examples→检索→清理，退出码 0 即通过
```

CI 在 macOS / Windows / Ubuntu × Python 3.8/3.11 上跑同一套冒烟测试，并对所有启动脚本做语法检查。

想接入新的导出格式，只需在 `app/importer.py` 里加一个解析器类（实现 `label` / `sniff` / `parse`），然后挂到文件末尾的 `PARSERS` 列表，检索与界面无需改动。细节见 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 已知限制

- 分词粒度是字符 bigram：≥2 字的词走索引（毫秒级），单字查询回退 `LIKE` 全表扫描（80 万条约 1 秒）
- 不支持图片 / 语音内容检索（源数据无文字）
- Windows 上中文文件名解压需系统支持 UTF-8（Win10 及以上默认可以）

## License

[MIT](LICENSE)
