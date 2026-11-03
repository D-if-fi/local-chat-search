---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: dc1f9365f5c0b69ca1bfc4be0972c4a3_d8a81ac8d75e11f18c3f52540064ee0f
    ReservedCode1: 18B1R7xFoOfnGxxPC0kKRF9zuxWz5EE6x6qztbLo/sqSS3dpjyFNRhmH0htvo5YKfsutOeySjm/m6RjqY1lc5DzuZuu/0PBi7Yb2xb3vvYF0fedEv2ISgiTbaIKfiH9HIMTumULa4G1CxAT0oAAkQqwKdAD1Un9GQc3wvuDMLiTn7G/no4/uycjmP+A=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: dc1f9365f5c0b69ca1bfc4be0972c4a3_d8a81ac8d75e11f18c3f52540064ee0f
    ReservedCode2: 18B1R7xFoOfnGxxPC0kKRF9zuxWz5EE6x6qztbLo/sqSS3dpjyFNRhmH0htvo5YKfsutOeySjm/m6RjqY1lc5DzuZuu/0PBi7Yb2xb3vvYF0fedEv2ISgiTbaIKfiH9HIMTumULa4G1CxAT0oAAkQqwKdAD1Un9GQc3wvuDMLiTn7G/no4/uycjmP+A=
---

# 贡献指南

感谢愿意改进这个项目。为了不破坏「零依赖、数据不出本机」这两条底线，提交前请确认下面几点。

## 两条硬约束

1. **不引入第三方依赖**。服务端只用 Python 标准库，前端不用 CDN、不用构建工具。需要某个能力时优先手写实现。
2. **不引入任何联网行为**。不加遥测、不加远程字体/图标、不做版本检查、不请求外部接口。数据只能待在本机。

任何破坏这两条的 PR 都会被拒绝，无论功能多好。

## 提交前自检

```bash
python3 tests/smoke_test.py       # 必须退出码 0
python3 -m py_compile app/server.py app/importer.py tools/csv_to_jsonl.py
```

另外确认：

- `git status` 里没有 `data/`、`*.db`、你自己的导出包（这是最容易犯的错，等于泄露聊天记录）
- 新增/改动的逻辑有对应的断言写进 `tests/smoke_test.py`
- 中文注释与用户可见文案保持中文（英文文档同步更新到 `README.en.md`）

## 加一个导出格式适配器

见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#加一种新格式)。要点：

- 实现 `label` / `sniff(zf)` / `parse(zf, progress=None)`，逐条 `yield` 统一字典
- `mid` 必须**稳定可复现**（同一份包重复解析得到相同 mid），否则去重会失效
- `sniff` 要写得足够严格，避免把别的格式误判成自己的；检测顺序由 `PARSERS` 列表决定
- 在 `examples/` 里放一份**脱敏**的样例（自己编造几个人的对话即可，不要用真实记录）

## 提交信息

沿用 Conventional Commits 风格，一句话说清改了什么：

```
feat(importer): 支持钉钉导出包
fix(server): 单文件上传时保留真实扩展名
docs: 补充 Windows 解压乱码说明
```

## 分支与 PR

- 从 `main` 切分支，PR 目标为 `main`
- 一个 PR 只做一件事，附带「动机 + 改动点 + 验证方式」
- UI 改动请附截图

## 报告问题

请用 Issue 模板，附上：

- 操作系统与 Python 版本
- 复现步骤（能脱敏的尽量脱敏）
- 报错信息或截图

**不要**在 Issue 里粘贴真实聊天记录、导出包或数据库文件。需要样例数据时，请自己编一份结构相同的假数据。
*（内容由AI生成，仅供参考）*
