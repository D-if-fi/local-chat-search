#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端冒烟测试：把仓库自带的 examples/ 导入一个临时库，跑检索，最后清理。

用法（仓库根目录执行）：
    python3 tests/smoke_test.py

不依赖任何第三方库，CI 与本地均可直接跑。退出码 0 表示通过。
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = ["demo.json", "demo.jsonl", "demo.txt"]
EXPECT_TOTAL = 14          # examples 三个文件的预期总条数


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def api(port, path, timeout=30):
    with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=timeout) as r:
        return json.load(r)


def upload(port, path):
    name = os.path.basename(path)
    url = "http://127.0.0.1:%d/api/import/upload?name=%s" % (port, urllib.parse.quote(name))
    with open(path, "rb") as f:
        body = f.read()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def wait_import(port, limit=120):
    deadline = time.time() + limit
    while time.time() < deadline:
        time.sleep(1)
        st = api(port, "/api/import/status")
        if st["state"] in ("done", "error"):
            return st
    raise AssertionError("导入超时")


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("  ✓ %s" % msg)


def main():
    workdir = tempfile.mkdtemp(prefix="chatsearch-smoke-")
    data_dir = os.path.join(workdir, "data")
    port = free_port()
    env = dict(os.environ, CHAT_SEARCH_DATA=data_dir)
    log = open(os.path.join(workdir, "server.log"), "w")
    server = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "app", "server.py"), str(port)],
        cwd=ROOT, env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL)
    try:
        # 等端口起来
        for _ in range(50):
            try:
                api(port, "/api/stats", timeout=3)
                break
            except Exception:
                time.sleep(0.4)
        else:
            raise AssertionError("服务未能启动，日志见 %s" % log.name)

        print("[1] 空库启动")
        st = api(port, "/api/stats")
        check(st["empty"] is True, "首次启动为空库（会弹导入向导）")
        check(urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=10).status == 200,
              "首页可访问")

        print("[2] 导入 examples 里的三种格式")
        for name in EXAMPLES:
            upload(port, os.path.join(ROOT, "examples", name))
            st = wait_import(port)
            check(st["state"] == "done" and st["inserted"] > 0,
                  "%s 导入 %s 条（来源：%s）" % (name, st["inserted"], st["source"]))
        st = api(port, "/api/stats")
        check(st["messages"] == EXPECT_TOTAL, "总条数 = %d" % EXPECT_TOTAL)
        check(st["chats"] == 4, "会话数 = 4（不同文件没有被并成一个桶）")

        print("[3] 重复导入应 0 新增")
        for name in EXAMPLES:
            upload(port, os.path.join(ROOT, "examples", name))
            st = wait_import(port)
            check(st["inserted"] == 0, "%s 重复导入 0 新增" % name)
        check(api(port, "/api/stats")["messages"] == EXPECT_TOTAL, "总数未变")

        print("[4] 检索")
        r = api(port, "/api/search?q=%s&limit=10" % urllib.parse.quote("割接"))
        check(r["total"] >= 2, "双字词「割接」命中 %d 条" % r["total"])
        r = api(port, "/api/search?q=%s&limit=10" % urllib.parse.quote("审批"))
        check(r["total"] >= 1, "「审批」命中 %d 条" % r["total"])
        r = api(port, "/api/search?q=%s&limit=10" % urllib.parse.quote("好"))
        check(r["total"] >= 1, "单字「好」回退 LIKE 命中 %d 条" % r["total"])
        r = api(port, "/api/search?q=%s&limit=5" % urllib.parse.quote("补充说明"))
        check(r["total"] >= 1, "txt 续行已并入上一条（可搜到「补充说明」）")

        print("\n全部通过")
        return 0
    finally:
        try:
            server.terminate()
            server.wait(timeout=5)
        except Exception:
            server.kill()
        log.close()
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
