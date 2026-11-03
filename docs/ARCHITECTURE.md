---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: dc1f9365f5c0b69ca1bfc4be0972c4a3_da968e81d75e11f18c3f52540064ee0f
    ReservedCode1: fAkR6jLSTI/+ynP6cFuhoQZliscpHxGnpRJF3VoZ5dy48TiTT775yvojnGfkernhZtXK9hJZ3sL+2KZlRjBlhWJxZE/VXIA9qNbtOWBzThuhz2maBw4IVmNpUYSC6Jgu8MdPTE8L3/ePXILzCRC2/BdQ0GoBwSumSxBtrH3F2H9Bz8LC6sHKQiR24Qc=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: dc1f9365f5c0b69ca1bfc4be0972c4a3_da968e81d75e11f18c3f52540064ee0f
    ReservedCode2: fAkR6jLSTI/+ynP6cFuhoQZliscpHxGnpRJF3VoZ5dy48TiTT775yvojnGfkernhZtXK9hJZ3sL+2KZlRjBlhWJxZE/VXIA9qNbtOWBzThuhz2maBw4IVmNpUYSC6Jgu8MdPTE8L3/ePXILzCRC2/BdQ0GoBwSumSxBtrH3F2H9Bz8LC6sHKQiR24Qc=
---

# 架构说明

代码总量约 1400 行，三个文件，没有框架。这份文档说明数据怎么流动、索引为什么这么设计，以及你想加东西时应该改哪里。

## 数据流

```
导出包 (zip / json / jsonl / txt)
        │
        ▼  app/importer.py
   detect() 嗅探格式 → 选定 Parser 类
   Parser.parse() 产出统一消息字典
        │   {mid, chat_id, chat_name, mode, sender, msg_type, ts, text, deleted, position}
        ▼
   server.py import_worker()（后台线程）
        │  INSERT OR IGNORE msg(...)   ← 按 mid 去重
        │  同时写 msg_bi(rowid, bi)     ← 检索索引
        │  汇总 chat 表 + meta 表
        ▼
   data/chat_search.db
        │
        ▼  /api/search
   tokenize() → 每个词判定走索引还是 LIKE → 组合过滤 → 排序分页
        │
        ▼  index.html
   单页界面：搜索框 / 筛选 / 结果 / 上下文抽屉
```

## 表结构

| 表 | 作用 |
| --- | --- |
| `msg` | 消息主表：`mid`（唯一 ID）、`chat_id`、`chat_name`、`mode`、`sender`、`msg_type`、`ts`、`text`、`deleted`、`position` |
| `msg_bi` | FTS5 虚表（`tokenize='unicode61'`），每行存消息 `text` 的 bigram 编码串 |
| `chat` | 会话聚合：名称、消息数、起止时间；每次导入后按 `msg` 全量重算 `cnt` |
| `meta` | 键值对：`last_import`、`source` |

索引：`msg(ts)`、`msg(chat_id)`、`msg(sender)`、`msg(mid)`。

## 为什么用字符 bigram 而不是 trigram

FTS5 内置 trigram 分词器要求查询串**至少 3 个字符**，中文两字词（「割接」「带宽」「退款」）直接 0 命中——这是这类工具最刚需的场景，所以不能用。

做法是自己编码：入库和查询走同一个 `encode_text_bigram()`，先把文本按「数字 / 字母 / 下划线 / 中文」切成片段，片段内相邻两字两两成词用空格连接，片段之间插 `|` 分隔符，避免跨词假匹配。查询时把关键词编码成短语（`"边 缘 计 算"` 形式）走 `msg_bi MATCH`。

结果：两字词命中在毫秒级，与 `LIKE` 全表扫的结果计数一致。

单字查询无法形成 bigram，显式回退到 `LIKE ... ESCAPE '\'` 全表扫描——80 万行约 1 秒，本地单用户场景可接受。

## 检索路由

`/api/search?q=...` 的处理顺序：

1. 按空格 / 引号切词；引号内的词作为整体短语，做短语匹配
2. 每个词独立判定：≥2 个字符走 `msg_bi MATCH`，单字符走 `LIKE`
3. 多个词取交集（AND）
4. 叠加过滤条件：`chat_id`、`sender`、`start`/`end` 日期、`mtype`、`deleted`
5. 排序（默认按时间倒序）后分页，返回 `snippet`（命中位置前后各截一段）

`/api/context` 按 `position` 取该消息前后各 12 条，用于结果详情面板。

## 导入并发与去重

- 上传接口把文件按**真实扩展名**落到 `data/upload_<ts>.<ext>`，起一个后台线程解析，前端轮询 `/api/import/status`
- 单文件导入时用上传的文件名作为会话名（JSON 里带 `chat_name` 则优先用 `chat_name`），避免多个文件被并成同一个会话桶
- 去重完全靠 `mid`：解析器优先用源数据自带的 `message_id`，没有则由 `chat_id + ts + sender + text` 哈希生成，因此同一份包重复导入是幂等的
- 用 `INSERT OR IGNORE` + 每 2000 条提交一次，边导边可查

## 加一种新格式

在 `app/importer.py` 里实现一个类：

```python
class MyParser:
    label = "我的导出格式"          # 界面上显示的来源名

    @staticmethod
    def sniff(zf):                  # 判断这个 zip / 文件是不是我的格式
        return any(n.endswith(".myext") for n in zf.namelist())

    @staticmethod
    def parse(zf, progress=None):   # 逐条 yield 统一字典
        yield {"mid": ..., "chat_id": ..., "chat_name": ..., "mode": "group",
               "sender": ..., "msg_type": "text", "ts": "2024-03-01 10:20:00",
               "text": ..., "deleted": 0, "position": None}
```

然后加到文件末尾的 `PARSERS = [FeishuParser, JsonParser, TxtParser, MyParser]`。检索、界面、导入流程都不用动。

## 前端

`app/index.html` 单文件，无构建步骤，无外部 CDN：原生 `fetch` + DOM 操作，样式内联。首次打开（`/api/stats` 返回 `empty=true`）显示导入向导；页面任意位置可拖入文件追加导入。
*（内容由AI生成，仅供参考）*
