#!/usr/bin/env python3
"""把 local-chat-search 打包成「免安装、双击即用」的可执行文件。

用法（需要先装 PyInstaller）：
    pip install pyinstaller
    python tools/build_app.py

产物：
    macOS   -> build/dist/local-chat-search.app   （双击运行，无需 Python）
    Windows -> build/dist/local-chat-search.exe   （双击运行，无需 Python）
    Linux   -> build/dist/local-chat-search       （给愿意用命令行的 Linux 用户）

只有发布者需要运行这个脚本；普通用户直接下载 Release 里的成品即可。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "local-chat-search"


def build() -> str:
    work = os.path.join(ROOT, "build", "work")
    dist = os.path.join(ROOT, "build", "dist")
    for d in (work, dist):
        shutil.rmtree(d, ignore_errors=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", NAME,
        "--add-data", f"app/index.html{os.pathsep}app",
        "--workpath", work,
        "--distpath", dist,
    ]
    if sys.platform == "darwin":
        cmd.append("--windowed")          # 生成 .app，双击不弹终端窗口
    elif sys.platform == "win32":
        cmd.append("--onefile")           # 生成单个 exe
    else:
        cmd.append("--onefile")
    cmd.append(os.path.join("app", "server.py"))

    print("运行:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)

    if sys.platform == "darwin":
        return os.path.join(dist, NAME + ".app")
    if sys.platform == "win32":
        return os.path.join(dist, NAME + ".exe")
    return os.path.join(dist, NAME)


if __name__ == "__main__":
    out = build()
    size = 0
    if os.path.isdir(out):
        for root, _dirs, files in os.walk(out):
            size += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    else:
        size = os.path.getsize(out)
    print(f"\n完成: {out}  ({size / 1024 / 1024:.1f} MB)")
