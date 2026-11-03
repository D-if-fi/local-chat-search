#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 CSV 转成检索工具能直接导入的 JSONL。

适用场景：手上有 Excel / 数据库 / 其它工具导出的 CSV 聊天表（列名五花八门），
先转成通用 JSONL，再拖进页面导入。

用法：
    python3 tools/csv_to_jsonl.py 聊天记录.csv -o 聊天记录.jsonl --chat "某某群"
    python3 tools/csv_to_jsonl.py 聊天记录.csv --chat-col 群名称 > 输出.jsonl

列名自动识别（大小写、下划线、空格均不敏感）：
    时间: time create_time timestamp ts date datetime 时间 发送时间
    发送人: sender from name username author 发送人 昵称 用户
    内容: content text message msg body 内容 消息
    会话: chat_name chat group title conversation room 群名称 会话
"""
import argparse
import csv
import json
import sys

TIME_KEYS = ("time", "create_time", "createtime", "timestamp", "ts", "date", "datetime",
             "send_time", "sendtime", "时间", "发送时间", "日期")
SENDER_KEYS = ("sender", "from", "name", "username", "author", "user", "nickname",
               "发送人", "发送者", "昵称", "用户", "发言人")
TEXT_KEYS = ("content", "text", "message", "msg", "body", "内容", "消息", "正文")
CHAT_KEYS = ("chat_name", "chat", "group", "title", "conversation", "room",
             "群名称", "会话", "群聊", "房间")


def norm(key):
    return (key or "").strip().lower().replace(" ", "").replace("-", "_")


def pick(headers, keys):
    """按优先级找第一个匹配的列名"""
    table = {norm(h): h for h in headers}
    for k in keys:
        if norm(k) in table:
            return table[norm(k)]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="CSV → 通用 JSONL（供 local-chat-search 导入）")
    ap.add_argument("csv_path", help="输入 CSV 文件路径")
    ap.add_argument("-o", "--out", help="输出 JSONL 路径，默认打印到标准输出")
    ap.add_argument("--chat", help="统一使用的会话名（CSV 里没有会话列时填这个）")
    ap.add_argument("--chat-col", help="用哪一列作为会话名，默认自动识别")
    ap.add_argument("--encoding", default="utf-8-sig", help="CSV 编码，默认 utf-8-sig（Excel 导出常用）")
    args = ap.parse_args(argv)

    with open(args.csv_path, newline="", encoding=args.encoding) as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        t_col, s_col, x_col = pick(headers, TIME_KEYS), pick(headers, SENDER_KEYS), pick(headers, TEXT_KEYS)
        c_col = args.chat_col or pick(headers, CHAT_KEYS)

        if not x_col:
            sys.exit("找不到内容列，请确认 CSV 表头里有 content / text / 内容 之一。\n实际表头: %s" % headers)
        if not t_col:
            print("警告：没找到时间列，导入后时间会是空的。实际表头: %s" % headers, file=sys.stderr)

        out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
        n = 0
        try:
            for row in reader:
                text = (row.get(x_col) or "").strip()
                if not text:
                    continue
                item = {
                    "sender": (row.get(s_col) or "").strip() if s_col else "",
                    "content": text,
                }
                if t_col:
                    item["time"] = (row.get(t_col) or "").strip()
                chat = (row.get(c_col) or "").strip() if c_col else ""
                item["chat_name"] = chat or args.chat or "未命名会话"
                out.write(json.dumps(item, ensure_ascii=False) + "\n")
                n += 1
        finally:
            if args.out:
                out.close()

    if args.out:
        print("已写入 %s（%d 条）" % (args.out, n), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
