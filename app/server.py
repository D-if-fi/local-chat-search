# -*- coding: utf-8 -*-
"""聊天记录本地检索服务（零第三方依赖，仅 Python 标准库）

用法： python3 server.py [端口]
默认 http://127.0.0.1:8777

首次打开会引导导入自己的聊天记录导出包；重复导入会自动合并去重。
"""
import os
import re
import sys
import json
import time
import shutil
import sqlite3
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DATA = os.environ.get("CHAT_SEARCH_DATA") or os.path.join(ROOT, "data")
DB = os.path.join(DATA, "chat_search.db")
INDEX = os.path.join(BASE, "index.html")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8777

sys.path.insert(0, BASE)
import importer  # noqa: E402

os.makedirs(DATA, exist_ok=True)

_lock = threading.Lock()
IMPORT = {"state": "idle", "phase": "", "done": 0, "total": 0,
          "messages": 0, "inserted": 0, "chats": 0, "error": "", "started": 0, "took": 0}

SCHEMA = """
CREATE TABLE IF NOT EXISTS msg(
  id INTEGER PRIMARY KEY,
  mid TEXT, chat_id TEXT, chat_name TEXT, mode TEXT,
  sender TEXT, msg_type TEXT, ts TEXT, text TEXT,
  deleted INTEGER DEFAULT 0, position INTEGER
);
CREATE INDEX IF NOT EXISTS idx_msg_ts ON msg(ts);
CREATE INDEX IF NOT EXISTS idx_msg_chat ON msg(chat_id);
CREATE INDEX IF NOT EXISTS idx_msg_sender ON msg(sender);
CREATE TABLE IF NOT EXISTS chat(
  chat_id TEXT PRIMARY KEY, name TEXT, mode TEXT,
  cnt INTEGER, first_ts TEXT, last_ts TEXT
);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS msg_bi USING fts5(bi, content='');
"""


def conn():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA cache_size=-120000")
    return c


def db_ready():
    if not os.path.exists(DB):
        return False
    try:
        with conn() as c:
            cols = [r[1] for r in c.execute("PRAGMA table_info(msg)")]
        return "mid" in cols
    except Exception:
        return False


def init_db():
    with conn() as c:
        c.executescript(SCHEMA)
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_msg_mid ON msg(mid)")


# ---------------------------------------------------------------- 编码 / 检索

SEG_RE = re.compile(r'[0-9a-z_\u4e00-\u9fff]+')


def encode_text_bigram(text):
    """与查询端 encode_term 同逻辑：分段后在段内取相邻两字"""
    out = []
    for s in SEG_RE.findall((text or "").lower()):
        if len(s) == 1:
            out.append(s)
        else:
            out.extend(s[i:i + 2] for i in range(len(s) - 1))
    return " ".join(out)


def tokenize(q):
    q = (q or "").strip()
    if not q:
        return []
    out = []
    for a, b in re.findall(r'"([^"]+)"|(\S+)', q):
        t = (a or b).strip()
        if t:
            out.append(t)
    return out


def esc_like(s):
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def encode_term(term):
    ps = []
    for s in SEG_RE.findall(term.lower()):
        if len(s) == 1:
            ps.append(s)
        else:
            ps.append('"' + " ".join(s[i:i + 2] for i in range(len(s) - 1)) + '"')
    return " AND ".join(ps)


def build_where(q, chat_id, sender, start, end, mtype, include_deleted):
    where, params = [], []
    fts_terms, like_terms = [], []
    for t in tokenize(q):
        (fts_terms if len(t) >= 2 else like_terms).append(t)

    if chat_id:
        where.append("m.chat_id = ?"); params.append(chat_id)
    if sender:
        where.append("m.sender = ?"); params.append(sender)
    if start:
        where.append("m.ts >= ?"); params.append(start)
    if end:
        where.append("m.ts <= ?"); params.append(end + " 99" if len(end) == 10 else end)
    if mtype:
        where.append("m.msg_type = ?"); params.append(mtype)
    if not include_deleted:
        where.append("m.deleted = 0")

    fts_match = None
    if fts_terms:
        fts_match = " AND ".join(encode_term(t) for t in fts_terms)
        where.append("m.id IN (SELECT rowid FROM msg_bi WHERE msg_bi MATCH ?)")
        params.append(fts_match)
    for t in like_terms:
        where.append("m.text LIKE ? ESCAPE '\\'")
        params.append("%" + esc_like(t) + "%")

    sql = (" WHERE " + " AND ".join(where)) if where else ""
    return sql, params, fts_match, like_terms, fts_terms + like_terms


def make_snippet(text, terms, width=140):
    text = text or ""
    if not terms:
        s = text[:width]
        return s + ("…" if len(text) > width else "")
    low = text.lower()
    pos = -1
    for t in terms:
        p = low.find(t.lower())
        if p != -1 and (pos == -1 or p < pos):
            pos = p
    if pos == -1:
        pos = 0
    start = max(0, pos - 40)
    end = min(len(text), pos + width)
    s = re.sub(r"\s+", " ", text[start:end].replace("\n", " "))
    return ("…" if start > 0 else "") + s + ("…" if end < len(text) else "")


# ---------------------------------------------------------------- 导入

ALLOWED_EXTS = (".zip", ".txt", ".log", ".md", ".json", ".jsonl", ".ndjson")

def import_worker(zip_path, replace=False, display_name=""):
    t0 = time.time()
    try:
        IMPORT.update(state="running", phase="准备中", done=0, total=0,
                      messages=0, inserted=0, chats=0, error="", started=t0, took=0)

        if replace and os.path.exists(DB):
            for suffix in ("", "-wal", "-shm"):
                p = DB + suffix
                if os.path.exists(p):
                    os.remove(p)
        init_db()

        cls = importer.detect(zip_path)
        IMPORT["source"] = cls.label

        def prog(i, n):
            IMPORT["done"] = i
            IMPORT["total"] = n
            IMPORT["phase"] = "解析文件 %d/%d" % (i, n)

        IMPORT["phase"] = "解析中"
        c = conn()
        cur = c.cursor()
        batch = []
        seen_chats = {}
        total_msgs = 0
        inserted = 0
        try:
            c.execute("BEGIN")
            for item in importer.parse_file(zip_path, prog, display_name):
                batch.append((
                    item["mid"], item["chat_id"], item["chat_name"], item["mode"],
                    item["sender"], item["msg_type"], item["ts"], item["text"],
                    item["deleted"], item["position"],
                ))
                cid = item["chat_id"]
                st = seen_chats.get(cid)
                if st is None:
                    seen_chats[cid] = [item["chat_name"], item["mode"], item["ts"], item["ts"], 1]
                else:
                    if item["ts"] and (not st[2] or item["ts"] < st[2]):
                        st[2] = item["ts"]
                    if item["ts"] and (not st[3] or item["ts"] > st[3]):
                        st[3] = item["ts"]
                    st[4] += 1

                if len(batch) >= 2000:
                    inserted += _flush(c, cur, batch)
                    total_msgs += len(batch)
                    batch = []
                    IMPORT["messages"] = total_msgs
                    IMPORT["inserted"] = inserted
                    IMPORT["phase"] = "已处理 %s 条" % format(total_msgs, ",")
            if batch:
                inserted += _flush(c, cur, batch)
                total_msgs += len(batch)
                IMPORT["messages"] = total_msgs
                IMPORT["inserted"] = inserted
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

        IMPORT["phase"] = "更新会话索引"
        c = conn()
        try:
            with c:
                for cid, st in seen_chats.items():
                    c.execute(
                        "INSERT INTO chat(chat_id, name, mode, cnt, first_ts, last_ts) "
                        "VALUES(?,?,?,?,?,?) ON CONFLICT(chat_id) DO UPDATE SET "
                        "name=excluded.name, "
                        "first_ts=CASE WHEN chat.first_ts='' OR chat.first_ts IS NULL "
                        "THEN excluded.first_ts ELSE min(chat.first_ts, excluded.first_ts) END, "
                        "last_ts=CASE WHEN chat.last_ts='' OR chat.last_ts IS NULL "
                        "THEN excluded.last_ts ELSE max(chat.last_ts, excluded.last_ts) END",
                        (cid, st[0], st[1], st[4], st[2], st[3]))
                c.execute("UPDATE chat SET cnt=(SELECT count(*) FROM msg WHERE msg.chat_id=chat.chat_id)")
                c.execute("INSERT INTO meta(k,v) VALUES('last_import',?) "
                          "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                          (time.strftime("%Y-%m-%d %H:%M:%S"),))
                c.execute("INSERT INTO meta(k,v) VALUES('source',?) "
                          "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (cls.label,))
            c.execute("ANALYZE")
        finally:
            c.close()

        IMPORT.update(state="done", phase="完成", took=round(time.time() - t0, 1),
                      messages=total_msgs, inserted=inserted, chats=len(seen_chats))
    except Exception as e:
        IMPORT.update(state="error", phase="失败", error=str(e),
                      took=round(time.time() - t0, 1))
    finally:
        try:
            os.remove(zip_path)
        except Exception:
            pass


def _flush(c, cur, batch):
    """写入一批消息，返回实际新增条数（已存在的按 mid 忽略）"""
    n = 0
    for row in batch:
        cur.execute(
            "INSERT OR IGNORE INTO msg(mid, chat_id, chat_name, mode, sender, msg_type, ts, text, deleted, position) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)", row)
        if cur.rowcount:
            cur.execute("INSERT INTO msg_bi(rowid, bi) VALUES(?,?)",
                        (cur.lastrowid, encode_text_bigram(row[7])))
            n += 1
    c.commit()
    c.execute("BEGIN")
    return n


# ---------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "ChatSearch/2.0"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # ---- 上传（原始二进制流，不依赖 multipart）
    def do_POST(self):
        try:
            u = urlparse(self.path)
            qs = parse_qs(u.query)

            if u.path == "/api/import/upload":
                if IMPORT["state"] == "running":
                    return self._send(409, {"error": "已有导入任务在进行中"})
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0:
                    return self._send(400, {"error": "空文件"})
                if length > 4 * 1024 ** 3:
                    return self._send(413, {"error": "文件超过 4GB"})
                name = (qs.get("name") or [""])[0]
                ext = os.path.splitext(os.path.basename(name))[1].lower()
                if ext not in ALLOWED_EXTS:
                    ext = ".zip"
                tmp = os.path.join(DATA, "upload_%d%s" % (int(time.time() * 1000), ext))
                got = 0
                with open(tmp, "wb") as f:
                    while got < length:
                        chunk = self.rfile.read(min(1024 * 512, length - got))
                        if not chunk:
                            break
                        f.write(chunk)
                        got += len(chunk)
                if got != length:
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass
                    return self._send(400, {"error": "上传不完整"})
                replace = (qs.get("replace") or ["0"])[0] == "1"
                IMPORT.update(state="running", phase="已接收文件", done=0, total=0,
                              messages=0, inserted=0, chats=0, error="", started=time.time(), took=0)
                threading.Thread(target=import_worker, args=(tmp, replace, name), daemon=True).start()
                return self._send(200, {"ok": True, "size": got})

            if u.path == "/api/import/reset":
                if IMPORT["state"] == "running":
                    return self._send(409, {"error": "导入进行中，无法清空"})
                for suffix in ("", "-wal", "-shm"):
                    p = DB + suffix
                    if os.path.exists(p):
                        os.remove(p)
                init_db()
                return self._send(200, {"ok": True})

            self._send(404, {"error": "not found"})
        except BrokenPipeError:
            pass
        except Exception as e:
            try:
                self._send(500, {"error": str(e)})
            except Exception:
                pass

    def do_GET(self):
        try:
            u = urlparse(self.path)
            p, qs = u.path, parse_qs(u.query)

            def g(k, d=""):
                v = qs.get(k)
                return v[0] if v else d

            if p in ("/", "/index.html"):
                with open(INDEX, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            if p == "/api/import/status":
                return self._send(200, IMPORT)

            if not db_ready():
                if p == "/api/stats":
                    return self._send(200, {"empty": True})
                return self._send(200, [] if p in ("/api/chats", "/api/senders", "/api/types")
                                  else {"empty": True})

            if p == "/api/stats":
                with conn() as c:
                    row = c.execute(
                        "SELECT count(*) n, count(DISTINCT chat_id) chats, "
                        "count(DISTINCT sender) senders, min(ts) t0, max(ts) t1 FROM msg").fetchone()
                    src = c.execute("SELECT v FROM meta WHERE k='source'").fetchone()
                    lst = c.execute("SELECT v FROM meta WHERE k='last_import'").fetchone()
                size = os.path.getsize(DB) if os.path.exists(DB) else 0
                return self._send(200, {
                    "empty": row["n"] == 0,
                    "messages": row["n"], "chats": row["chats"], "senders": row["senders"],
                    "first": row["t0"], "last": row["t1"],
                    "db_mb": round(size / 1024 / 1024),
                    "source": (src["v"] if src else ""),
                    "last_import": (lst["v"] if lst else ""),
                })

            if p == "/api/chats":
                kw = g("q").strip()
                with conn() as c:
                    if kw:
                        rows = c.execute(
                            "SELECT chat_id, name, mode, cnt, first_ts, last_ts FROM chat "
                            "WHERE name LIKE ? ORDER BY cnt DESC LIMIT 300",
                            ("%" + esc_like(kw) + "%",)).fetchall()
                    else:
                        rows = c.execute(
                            "SELECT chat_id, name, mode, cnt, first_ts, last_ts FROM chat "
                            "ORDER BY cnt DESC LIMIT 300").fetchall()
                return self._send(200, [dict(r) for r in rows])

            if p == "/api/senders":
                kw = g("q").strip()
                with conn() as c:
                    rows = c.execute(
                        "SELECT sender, count(*) n FROM msg WHERE sender != '' "
                        "AND sender LIKE ? GROUP BY sender ORDER BY n DESC LIMIT 200",
                        ("%" + esc_like(kw) + "%",)).fetchall()
                return self._send(200, [dict(r) for r in rows])

            if p == "/api/types":
                with conn() as c:
                    rows = c.execute(
                        "SELECT msg_type, count(*) n FROM msg GROUP BY msg_type "
                        "ORDER BY n DESC").fetchall()
                return self._send(200, [dict(r) for r in rows])

            if p == "/api/search":
                q, chat_id, sender = g("q"), g("chat_id"), g("sender")
                start, end, mtype = g("start"), g("end"), g("mtype")
                inc_del = g("deleted") == "1"
                try:
                    limit = min(int(g("limit", "50")), 200)
                    offset = max(int(g("offset", "0")), 0)
                except ValueError:
                    limit, offset = 50, 0

                t0 = time.time()
                sql, params, fts_match, like_terms, terms = build_where(
                    q, chat_id, sender, start, end, mtype, inc_del)
                with conn() as c:
                    total = c.execute("SELECT count(*) FROM msg m" + sql, params).fetchone()[0]
                    rows = c.execute(
                        "SELECT m.id, m.chat_id, m.chat_name, m.sender, m.msg_type, m.ts, m.text, m.deleted "
                        "FROM msg m" + sql + " ORDER BY m.ts DESC, m.id DESC LIMIT ? OFFSET ?",
                        params + [limit, offset]).fetchall()
                items = []
                for r in rows:
                    items.append({
                        "id": r["id"], "chat_id": r["chat_id"], "chat_name": r["chat_name"],
                        "sender": r["sender"], "msg_type": r["msg_type"], "ts": r["ts"],
                        "deleted": r["deleted"],
                        "snippet": make_snippet(r["text"], terms),
                        "len": len(r["text"] or ""),
                    })
                return self._send(200, {
                    "total": total, "items": items, "terms": terms,
                    "took_ms": int((time.time() - t0) * 1000),
                    "mode": "fts" if fts_match else ("like" if terms else "list"),
                })

            if p == "/api/context":
                try:
                    mid = int(g("id"))
                    before = min(int(g("before", "12")), 200)
                    after = min(int(g("after", "12")), 200)
                except ValueError:
                    return self._send(400, {"error": "bad id"})
                with conn() as c:
                    m = c.execute("SELECT * FROM msg WHERE id=?", (mid,)).fetchone()
                    if not m:
                        return self._send(404, {"error": "not found"})
                    if m["position"] is None:
                        rows = c.execute(
                            "SELECT * FROM msg WHERE chat_id=? AND ts<=? ORDER BY ts DESC LIMIT ?",
                            (m["chat_id"], m["ts"], before + after + 1)).fetchall()
                        rows = sorted(rows, key=lambda r: (r["ts"], r["id"]))
                    else:
                        rows = c.execute(
                            "SELECT * FROM msg WHERE chat_id=? AND position BETWEEN ? AND ? "
                            "ORDER BY position",
                            (m["chat_id"], m["position"] - before, m["position"] + after)).fetchall()
                return self._send(200, {
                    "chat_id": m["chat_id"], "chat_name": m["chat_name"], "focus": mid,
                    "items": [{
                        "id": r["id"], "sender": r["sender"], "ts": r["ts"],
                        "msg_type": r["msg_type"], "text": r["text"], "deleted": r["deleted"],
                    } for r in rows],
                })

            self._send(404, {"error": "not found"})
        except BrokenPipeError:
            pass
        except Exception as e:
            try:
                self._send(500, {"error": str(e)})
            except Exception:
                pass


def main():
    # Windows 控制台与重定向输出默认不是 UTF-8，打印中文会 UnicodeEncodeError 直接把服务打断
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    if db_ready():
        print("数据库: %s" % DB)
    else:
        print("尚未导入聊天记录，打开网页后可直接拖入导出包")
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("聊天记录检索已启动: http://127.0.0.1:%d" % PORT)
    print("按 Ctrl+C 停止")
    if not os.environ.get("CHAT_SEARCH_NO_BROWSER"):
        try:
            import webbrowser
            threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:%d" % PORT)).start()
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
