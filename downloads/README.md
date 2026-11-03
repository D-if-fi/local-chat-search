# 直接下载 / Direct download

不用装 Python、不用开终端，点下面链接下载后双击即可使用。

| 平台 | 文件 | 说明 |
| --- | --- | --- |
| macOS | [`local-chat-search-macos.zip`](local-chat-search-macos.zip) | 解压后双击 `local-chat-search.app`（约 8 MB） |
| Windows | [`local-chat-search-windows.exe`](local-chat-search-windows.exe) | 双击即运行，单文件（约 9 MB） |

如果上面的链接点了没反应，用 raw 地址下载：

- https://github.com/D-if-fi/local-chat-search/raw/main/downloads/local-chat-search-macos.zip
- https://github.com/D-if-fi/local-chat-search/raw/main/downloads/local-chat-search-windows.exe

## 第一次打开需要放行一次

程序没有做代码签名（个人项目，签名证书要年费），所以系统会提示一次：

- **macOS**：提示「Apple 无法验证」→ 右键点 App → **打开** → 再点 **打开**。或到 系统设置 → 隐私与安全性 → 点 **仍要打开**。
- **Windows**：提示「Windows 已保护你的电脑」→ 点 **更多信息** → **仍要运行**。

## 数据在哪

| | 默认位置 | 便携模式（数据跟程序走） |
| --- | --- | --- |
| macOS | `~/Library/Application Support/local-chat-search/data` | 在 `.app` 同级建 `data/` 文件夹 |
| Windows | `%LOCALAPPDATA%\local-chat-search\data` | 在 `.exe` 同级建 `data/` 文件夹 |

## 说明

- 这里的文件是发布用的成品，每个版本由 `.github/workflows/release.yml` 自动构建，同时也会附到 [Releases](https://github.com/D-if-fi/local-chat-search/releases) 页。
- 只从本仓库或 Releases 下载，别用第三方转载的包。
- Linux 用户请用源码运行：`./start.sh`（见仓库根目录 README）。
