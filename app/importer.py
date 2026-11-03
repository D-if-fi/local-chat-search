# -*- coding: utf-8 -*-
"""聊天记录导入器：把各家导出的聊天文件解析成统一结构

支持格式
  feishu  : 飞书导出包（zip 内含 chats/*.json + chat_list.json）
  json    : 单个/多个 JSON 文件，自动识别时间、发送人、内容字段
  txt     : 常见的纯文本导出（行首带时间戳，如 "2024-01-01 12:00 张三: 内容"）

统一输出字段：
  chat_id, chat_name, mode, mid, sender, msg_type, ts, text, deleted, position
"""
import os
import re
import json
import zipfile
import hashlib

# ---------------------------------------------------------------- 文本清洗

RE_FILE = re.compile(r'<file\s+[^>]*name="([^"]*)"[^>]*/?>')
RE_VIDEO = re.compile(r'<video\s+[^>]*name="([^"]*)"[^>]*/?>')
RE_FOLDER = re.compile(r'<folder\s+[^>]*name="([^"]*)"[^>]*>(.*?)</folder>', re.S)
RE_TAG = re.compile(r'<[^>]{1,120}>')
RE_CARD = re.compile(r'<card\s+[^>]*title="([^"]*)"[^>]*>(.*?)</card>', re.S)
RE_AT = re.compile(r'@_user_\d+')
RE_MDIMG = re.compile(r'!\[[^\]]*\]\([^)]*\)')

PLACEHOLDER = {
    "image": "[图片]", "sticker": "[表情]", "video_chat": "[通话]",
    "nonsupport": "[不支持的消息类型]", "media": "[视频]",
}


def clean_text(c, msg_type="text"):
    if c is None:
        return ""
    if not isinstance(c, str):
        try:
            c = json.dumps(c, ensure_ascii=False)
        except Exception:
            return str(c)

    s = c
    m = RE_CARD.search(s)
    if m:
        s = (m.group(1) or "") + "\n" + (m.group(2) or "")

    def _folder(mm):
        names = RE_FILE.findall(mm.group(2) or "")
        return "[文件夹: %s]%s" % (mm.group(1), (" " + " ".join(names)) if names else "")

    s = RE_FOLDER.sub(_folder, s)
    s = RE_FILE.sub(lambda m: "[文件: %s]" % m.group(1), s)
    s = RE_VIDEO.sub(lambda m: "[视频: %s]" % m.group(1), s)
    s = RE_MDIMG.sub("[图片]", s)
    s = RE_TAG.sub(" ", s)
    s = s.replace("\u200b", "").replace("\u200c", "").replace("\ufeff", "")
    s = RE_AT.sub("", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()

    if not s or s in ("[Image]", "[Sticker]", "[Video call]", "[nonsupport]",
                      "[Invalid text JSON]", "[消息]"):
        return PLACEHOLDER.get(msg_type, "[消息内容导出失败]")
    return s


def make_mid(*parts):
    """没有原始消息 ID 时，用内容指纹去重"""
    h = hashlib.md5(("\x1f".join("" if p is None else str(p) for p in parts)).encode("utf-8"))
    return "h" + h.hexdigest()


# ---------------------------------------------------------------- 飞书

class FeishuParser:
    label = "飞书导出包"

    @staticmethod
    def sniff(zf):
        names = zf.namelist()
        return any(n.startswith("chats/") and n.endswith(".json") for n in names)

    @staticmethod
    def parse(zf, progress=None):
        names = [n for n in zf.namelist() if n.startswith("chats/") and n.endswith(".json")]
        names.sort()
        total = len(names)
        for i, n in enumerate(names):
            try:
                d = json.loads(zf.read(n).decode("utf-8", errors="replace"))
            except Exception:
                continue
            info = d.get("chat_info") or {}
            cid = info.get("chat_id") or os.path.basename(n).split("_")[0]
            cname = (info.get("name") or "").strip() or "(未命名会话)"
            mode = info.get("mode") or "group"
            for m in d.get("messages") or []:
                sender = (m.get("sender") or {}).get("name") or ""
                mtype = m.get("msg_type") or ""
                if not sender and mtype == "system":
                    sender = "系统"
                pos = m.get("message_position")
                try:
                    pos = int(pos)
                except Exception:
                    pos = None
                yield {
                    "chat_id": cid, "chat_name": cname, "mode": mode,
                    "mid": m.get("message_id") or make_mid(cid, m.get("create_time"), sender, m.get("content")),
                    "sender": sender.strip(), "msg_type": mtype,
                    "ts": m.get("create_time") or "",
                    "text": clean_text(m.get("content"), mtype),
                    "deleted": 1 if m.get("deleted") else 0,
                    "position": pos,
                }
            if progress and (i % 20 == 0 or i == total - 1):
                progress(i + 1, total)


# ---------------------------------------------------------------- 通用 JSON

TIME_KEYS = ("create_time", "createtime", "timestamp", "time", "ts", "date", "datetime", "send_time")
SENDER_KEYS = ("sender", "sender_name", "from", "from_name", "name", "nickname", "user", "talker")
TEXT_KEYS = ("content", "text", "message", "msg", "body", "strContent")
CHAT_KEYS = ("chat_name", "chat", "group", "room", "conversation", "talker_name")


def _pick(d, keys, default=""):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            v = d[k]
            if isinstance(v, dict):
                return v.get("name") or v.get("nickname") or v.get("id") or default
            return v
    return default


def _norm_ts(v):
    """把秒/毫秒时间戳或字符串统一成 'YYYY-MM-DD HH:MM'"""
    if v is None or v == "":
        return ""
    if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
        n = int(v)
        if n > 10 ** 11:
            n //= 1000
        import datetime
        try:
            return datetime.datetime.fromtimestamp(n).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(v)
    s = str(v).strip().replace("T", " ").replace("/", "-")
    return s[:16]


class JsonParser:
    label = "通用 JSON / JSONL 导出"

    @staticmethod
    def sniff(zf):
        return True  # 兜底适配器

    @staticmethod
    def parse(zf, progress=None):
        names = [n for n in zf.namelist()
                 if n.lower().endswith((".json", ".jsonl")) and not n.endswith("/")]
        if not names:
            return
        total = len(names)
        for i, n in enumerate(names):
            try:
                raw = zf.read(n).decode("utf-8", errors="replace")
            except Exception:
                continue
            data = None
            try:
                data = json.loads(raw)
            except Exception:
                # 尝试 JSONL
                rows = []
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
                data = rows or None
            if data is None:
                continue
            # 展开可能的容器字段
            if isinstance(data, dict):
                for k in ("messages", "data", "list", "items", "records", "chat"):
                    if isinstance(data.get(k), list):
                        data = data[k]
                        break
                else:
                    data = [data]
            if not isinstance(data, list):
                continue

            fname = os.path.basename(n)
            cid = os.path.splitext(fname)[0]
            for row in data:
                if not isinstance(row, dict):
                    continue
                # 会话标识优先级：行内 chat_id > 行内会话名 > 完整文件名（含扩展名，避免不同文件撞桶）
                cname = _pick(row, CHAT_KEYS, "")
                row_cid = (_pick(row, ("chat_id", "cid", "conversation_id", "room_id"), "")
                           or cname or fname)
                cname = cname or cid
                sender = _pick(row, SENDER_KEYS, "")
                ts = _norm_ts(_pick(row, TIME_KEYS, ""))
                text = _pick(row, TEXT_KEYS, "")
                yield {
                    "chat_id": str(row_cid), "chat_name": str(cname), "mode": "group",
                    "mid": row.get("message_id") or row.get("msg_id") or row.get("id")
                    or make_mid(row_cid, ts, sender, text),
                    "sender": str(sender).strip(), "msg_type": row.get("msg_type") or "text",
                    "ts": ts, "text": clean_text(text, row.get("msg_type") or "text"),
                    "deleted": 1 if row.get("deleted") else 0,
                    "position": None,
                }
            if progress:
                progress(i + 1, total)


# ---------------------------------------------------------------- TXT

TS_LINE = re.compile(
    r'^\s*[\[\(]?\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?\s*[\sT]?\d{1,2}:\d{2}(?::\d{2})?)\s*[\]\)]?\s*(.*)$'
)
SPEAKER = re.compile(r'^([^:：]{1,30})[:：]\s*(.*)$')


class TxtParser:
    label = "纯文本导出（行首时间戳）"

    @staticmethod
    def sniff(zf):
        return any(n.lower().endswith(".txt") for n in zf.namelist())

    @staticmethod
    def parse(zf, progress=None):
        names = [n for n in zf.namelist() if n.lower().endswith(".txt") and not n.endswith("/")]
        total = len(names)
        for i, n in enumerate(names):
            try:
                raw = zf.read(n).decode("utf-8", errors="replace")
            except Exception:
                continue
            # 完整文件名做 chat_id（含扩展名，避免不同 txt 撞桶），展示名去掉扩展名
            cid = os.path.basename(n) or "txt"
            cname = os.path.splitext(cid)[0]
            cur = None
            for line in raw.splitlines():
                m = TS_LINE.match(line)
                if m:
                    ts = _norm_ts(m.group(1).replace("年", "-").replace("月", "-").replace("日", ""))
                    rest = m.group(2)
                    sm = SPEAKER.match(rest)
                    if sm:
                        sender, text = sm.group(1), sm.group(2)
                    else:
                        sender, text = "", rest
                    if cur:
                        yield cur
                    cur = {
                        "chat_id": cid, "chat_name": cname, "mode": "group",
                        "mid": make_mid(cid, ts, sender, text),
                        "sender": sender.strip(), "msg_type": "text",
                        "ts": ts, "text": clean_text(text), "deleted": 0, "position": None,
                    }
                elif cur and line.strip():
                    cur["text"] = (cur["text"] + "\n" + line).strip()
            if cur:
                yield cur
            if progress:
                progress(i + 1, total)


PARSERS = [FeishuParser, JsonParser, TxtParser]

TEXT_EXTS = (".txt", ".log", ".md")
JSON_EXTS = (".json", ".jsonl", ".ndjson")
ZIP_EXTS = (".zip",)


class SingleFile:
    """把单个非 zip 文件包装成与 ZipFile 一致的读取接口"""

    def __init__(self, path, name=None):
        self.path = path
        self.name = name or os.path.basename(path)

    def namelist(self):
        return [self.name]

    def read(self, name=None):
        with open(self.path, "rb") as f:
            return f.read()


def _guess_by_content(path):
    """扩展名不可用时，按内容判断该用 JSON 还是 TXT 解析器"""
    try:
        with open(path, "rb") as f:
            head = f.read(4096).decode("utf-8", errors="replace").lstrip()
    except Exception:
        return JsonParser
    if head[:1] in ("[", "{"):
        return JsonParser
    if TS_LINE.match(head.splitlines()[0] if head.splitlines() else ""):
        return TxtParser
    return TxtParser if any(head) else JsonParser


def detect(path):
    """返回适用的解析器类；支持 zip 压缩包与单个 txt/json 文件"""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            for p in PARSERS:
                try:
                    if p.sniff(zf):
                        return p
                except Exception:
                    continue
        return JsonParser
    low = path.lower()
    if low.endswith(TEXT_EXTS):
        return TxtParser
    if low.endswith(JSON_EXTS):
        return JsonParser
    return _guess_by_content(path)


def parse_file(path, progress=None, display_name=None):
    cls = detect(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            for item in cls.parse(zf, progress):
                yield item
    else:
        # 单文件：用上传时的真实文件名当会话名，避免临时文件名污染
        src = SingleFile(path, display_name or os.path.basename(path))
        for item in cls.parse(src, progress):
            yield item
