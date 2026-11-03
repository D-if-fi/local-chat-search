# local-chat-search

[![CI](https://github.com/D-if-fi/local-chat-search/actions/workflows/ci.yml/badge.svg)](https://github.com/D-if-fi/local-chat-search/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)](#quick-start)

**Turn your exported chat history into a private, offline, full-text-searchable local database.**

Zero third-party dependencies — Python standard library only. One command, or one double-click. Everything stays in `data/chat_search.db` on your machine, the server binds `127.0.0.1` only, and nothing is uploaded anywhere.

English | [简体中文](README.zh-CN.md)

> **Just want to use it?** No Python needed — download and double-click:
> [macOS app](downloads/local-chat-search-macos.zip) · [Windows exe](downloads/local-chat-search-windows.exe)

![Screenshot](docs/screenshot.png)

## Why

A chat export is usually hundreds of JSON files inside a zip. Finding "what did we decide about that cutover window?" means scrolling for ten minutes. Uploading it to an online tool means handing a few years of conversations to a third party.

This project does exactly one thing: **make the export searchable on your own machine**, and give it a clean search page.

- 830k messages, real-world test: import in ~1–1.5 min, search in milliseconds
- Single process, no dependencies, no server, no account, no telemetry
- Format-agnostic: any export with a time / sender / content field will ingest

## Download (no Python, no terminal)

Non-technical users should start here: grab the prebuilt app from [**Releases**](https://github.com/D-if-fi/local-chat-search/releases/latest). Nothing to install.

| Platform | File | How to run |
| --- | --- | --- |
| macOS | `local-chat-search-macos.zip` | unzip → double-click `local-chat-search.app` |
| Windows | `local-chat-search-windows.exe` | double-click the `.exe` |

The app starts the local server and opens the search page by itself — no terminal window, no commands.

The builds are **unsigned**, so the very first launch asks for one extra click:

- **macOS** — "Apple could not verify…": right-click the app → **Open** → **Open** again. (Or System Settings → Privacy & Security → **Open Anyway**.)
- **Windows** — SmartScreen "Windows protected your PC": **More info** → **Run anyway**.

Where the data lives after that:

| | Default | Portable (keep next to the app) |
| --- | --- | --- |
| macOS | `~/Library/Application Support/local-chat-search/data` | create a `data/` folder next to the `.app` |
| Windows | `%LOCALAPPDATA%\local-chat-search\data` | create a `data/` folder next to the `.exe` |

Quit the app to stop the server (macOS: Ctrl-click the Dock icon → Quit; Windows: close the console window).

## Run from source

Requires **Python 3.8+** (macOS, Windows, Linux). No `pip install`, no virtualenv.

### Option A — one-click scripts

| Platform | Double-click | Or from terminal |
| --- | --- | --- |
| macOS | `start.command` | `./start.sh` |
| Windows | `start.bat` | `start.bat 8888` |
| Windows (PowerShell) | right-click → Run with PowerShell | `powershell -ExecutionPolicy Bypass -File .\start.ps1` |
| Linux | — | `./start.sh` |

All scripts auto-detect an installed Python 3.8+, start the server, and open `http://127.0.0.1:8777` in your browser.

### Option B — plain command

```bash
git clone https://github.com/D-if-fi/local-chat-search.git
cd local-chat-search
python3 app/server.py            # http://127.0.0.1:8777
```

### Common options

| What | How |
| --- | --- |
| Custom port | `./start.sh 8888` · `start.bat 8888` · `python3 app/server.py --port 8888` |
| Port taken | The server automatically retries 8777→8786 and prints the chosen port |
| Custom data location | `CHAT_SEARCH_DATA=~/my-chat-db python3 app/server.py` (Windows: set the same env var) |
| Don't open a browser | `CHAT_SEARCH_NO_BROWSER=1 python3 app/server.py` |
| Health check | `curl http://127.0.0.1:8777/api/health` |

On first launch the page shows an import wizard — drag your export zip onto the window and it ingests in the background. You can drop files onto the page at any time to add more.

> macOS: if double-clicking `start.command` says it "cannot be opened", right-click → Open, or run `chmod +x start.command start.sh` once.

## Build the binaries yourself

Releases are produced by GitHub Actions (`.github/workflows/release.yml`) on every `v*` tag. To build locally:

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install pyinstaller
python tools/build_app.py
```

Output: `build/dist/local-chat-search.app` (macOS) or `build/dist/local-chat-search.exe` (Windows). The runtime app still uses the standard library only — PyInstaller is a build-time tool, not a dependency of the shipped program.

## Supported input

| Input | Notes |
| --- | --- |
| Feishu / Lark export zip | zip containing `chats/*.json` + `chat_list.json`; chat name, sender, message type and recall state are detected |
| Generic JSON / JSONL | common field names auto-detected (see below); single file or zipped |
| Plain text | txt with a leading timestamp, e.g. `[2024-03-02 09:00:12] Alice: hello`; indented continuation lines are merged into the previous message |
| CSV | convert first with `tools/csv_to_jsonl.py`, then import the JSONL |

You don't need to rename fields — matching is case-, underscore- and space-insensitive:

| Meaning | Recognised field names |
| --- | --- |
| Time | `time` `create_time` `timestamp` `ts` `date` `datetime` (epoch seconds / ms or a date string) |
| Sender | `sender` `from` `name` `username` `author` |
| Content | `content` `text` `message` `msg` `body` |
| Conversation | `chat_name` `chat` `group` `title` `conversation` `room` |

Re-importing the same package is safe: messages are deduplicated by a stable message id, so you can just drop in each new export to merge incrementally.

`examples/` ships one sample per format so you can try the flow immediately.

## Search

- Full-text keyword search; space-separated terms mean AND
- Wrap terms in double quotes for exact phrase match, e.g. `"cutover window"`
- Filter by conversation, sender, date range and message type; optionally only recalled messages
- Click a hit to see 12 messages of surrounding context

Keyboard: `/` or `⌘K` focuses the search box, `↑`/`↓` moves through hits, `Enter` opens, `Esc` closes panels. Clicking a message copies it.

## Privacy

- All data lives in `data/chat_search.db`; delete the folder and you are back to a clean slate
- The server binds `127.0.0.1` only — other devices on your LAN cannot reach it
- `.gitignore` excludes `data/` and `*.db`, and CI fails if such a file is ever committed
- Images, voice, video and stickers carry no text in the source data, so only their placeholder markers are indexed — no OCR

## Project layout

```
local-chat-search/
├── app/
│   ├── server.py         local HTTP server + SQLite search (stdlib only)
│   ├── importer.py       export parsing and format adapters
│   └── index.html        single-page UI
├── tools/csv_to_jsonl.py CSV → JSONL converter
├── examples/             sample data in three formats
├── tests/smoke_test.py   end-to-end smoke test
├── docs/ARCHITECTURE.md  schema, index strategy, query routing
├── start.command         macOS double-click launcher
├── start.sh              macOS / Linux launcher
├── start.bat             Windows launcher (cmd)
└── start.ps1             Windows launcher (PowerShell)
```

## Development

```bash
python3 tests/smoke_test.py   # start → import examples → search → clean up; exit 0 = pass
```

CI runs the same smoke test on macOS, Windows and Ubuntu against Python 3.8 and 3.11, plus a syntax check of every launcher script.

To support a new export format, add one parser class to `app/importer.py` implementing `label` / `sniff` / `parse` and register it in the `PARSERS` list at the bottom — no changes needed in search or UI. See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Known limitations

- Tokenisation is character bigrams: terms of 2+ characters use the index (ms), single-character queries fall back to a `LIKE` scan (~1 s at 800k messages)
- No image / voice content search (the source data has no text for them)
- On Windows, non-ASCII filenames need UTF-8 support in the zip tooling (default on Windows 10+)

## License

[MIT](LICENSE)
