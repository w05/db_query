# FEATURE_EXPORT.md — 查询结果导出功能设计

> 文档目标：说明「多格式导出」「一键查询+导出自动化」「自然语言/界面触发导出」的设计思路与落地路径。  
> 范围：`db_query` 前端 + 后端 API + Claude Code Agent / 自定义 Command。

---

## 1. 背景与目标

### 1.1 业务目标

| 目标 | 说明 |
|------|------|
| 多格式导出 | 查询结果至少支持 **CSV**、**JSON** 两种下载格式 |
| 自动化流程 | 「执行查询 → 导出结果」可一键或通过一条命令完成 |
| 自然交互 | 查询完成后，系统可主动询问是否导出，或用自然语言触发导出 |

### 1.2 与现状的关系

当前 `Home.tsx` **已实现**前端侧 CSV / JSON 导出（Blob 下载）：

- 按钮：`EXPORT CSV` / `EXPORT JSON`
- CSV：RFC 4180 风格转义（逗号、引号、换行）
- JSON：`JSON.stringify(rows, null, 2)` 美化输出
- 文件名：`{database}_{ISO时间戳}.csv|.json`
- 行数 > 10000 时弹出确认 Modal
- 无结果时 `message.warning`

本设计在现有能力之上补齐：

1. 更清晰的产品与交互规范  
2. Claude Code 侧的「查询+导出」自动化命令  
3. AI / 自然语言触发导出的交互闭环  

---

## 2. 功能一：导出格式支持

### 2.1 设计原则

- **客户端优先**：结果已在浏览器内存中，导出不必再打后端（现状如此，延迟低、实现简单）。
- **格式最小集**：CSV + JSON 满足表格分析与程序消费两类场景。
- **可扩展**：统一导出服务接口，后续可加 TSV / Excel / Markdown 而不改调用方。

### 2.2 格式定义

| 格式 | MIME | 内容结构 | 适用场景 |
|------|------|----------|----------|
| CSV | `text/csv;charset=utf-8` | 首行表头 + 数据行；字段含 `,` `"` `\n` 时加双引号转义 | Excel / 数据仓库导入 |
| JSON | `application/json;charset=utf-8` | 行对象数组；`null` 保留为 JSON null | 脚本、API、二次处理 |

建议后续增强（可选）：

- CSV 增加 UTF-8 BOM（`\uFEFF`），改善 Excel 中文乱码  
- JSON 可选「带元数据」包装：`{ meta: { sql, exportedAt, rowCount }, data: [...] }`  
- 导出列顺序与结果表列顺序一致（已满足）

### 2.3 前端模块划分（建议）

将 `Home.tsx` 内联导出逻辑抽离为可复用模块：

```text
frontend/src/utils/exportResults.ts
  - exportToCSV(result, options)
  - exportToJSON(result, options)
  - buildFilename(dbName, format)
  - shouldWarnLarge(rowCount)
```

UI 层只负责：

- 无数据校验  
- 大结果确认  
- 成功 / 失败提示  

### 2.4 后端导出（可选增强，非必须）

若未来需要「服务端落盘 / 大结果流式导出 / 权限审计」：

```http
POST /api/v1/dbs/{name}/export
Content-Type: application/json

{
  "sql": "SELECT ...",
  "format": "csv" | "json",
  "filename": "optional_name"
}
```

响应：`Content-Disposition: attachment` 流式下载。

**首期不强制实现后端导出**；自动化命令可先走「查询 API + 本地写文件」。

### 2.5 验收标准

- [ ] 有结果时可下载合法 CSV，Excel/Numbers 可打开  
- [ ] 有结果时可下载合法 JSON，可被 `JSON.parse`  
- [ ] 字段含逗号、引号、换行时 CSV 不错位  
- [ ] 空结果禁止导出并提示  
- [ ] 超大数据量有确认拦截  

---

## 3. 功能二：自动化流程（Claude Code Agent / Command）

### 3.1 设计思路

将「连接库 → 执行 SQL → 拿到结果 → 写成文件」拆成可编排步骤，用 Claude Code 的 **自定义 Command** 或 **Agent Skill** 一键触发，减少人工点按钮。

推荐两层能力：

| 层级 | 形态 | 谁用 |
|------|------|------|
| A. 仓库内脚本 CLI | `scripts/query_export.py` / `npm run query:export` | 本地、CI、Agent 调用 |
| B. Claude Code Command | `.claude/commands/query-export.md` | 对话里 `/query-export` 一键跑 |

Agent 不直接操作浏览器 DOM，而是调用 **HTTP API + 写本地文件**，更稳定、可脚本化。

### 3.2 自动化流水线

```mermaid
flowchart LR
  A[输入: DB名 + SQL + 格式] --> B[健康检查 /health]
  B --> C[POST /api/v1/dbs/{name}/query]
  C --> D{成功?}
  D -->|否| E[输出错误并退出]
  D -->|是| F[按 format 序列化为 CSV/JSON]
  F --> G[写入 ./exports/ 目录]
  G --> H[返回文件路径给用户/Agent]
```

### 3.3 CLI 契约（建议）

```bash
# 示例：一键查询并导出
uv run python scripts/query_export.py \
  --base-url http://localhost:8000 \
  --db postgres \
  --sql "SELECT current_database() AS db, now() AS ts" \
  --format csv \
  --out ./exports
```

参数：

| 参数 | 说明 |
|------|------|
| `--db` | 已在 UI/API 中注册的连接名 |
| `--sql` | 要执行的 SELECT（或从 `--sql-file` 读） |
| `--format` | `csv` \| `json` |
| `--out` | 输出目录，默认 `./exports` |
| `--base-url` | 后端地址，默认 `http://localhost:8000` |

输出示例：

```text
OK rows=1 file=exports/postgres_2026-08-03T10-01-45.csv
```

### 3.4 Claude Code 自定义 Command 设计

在仓库增加：

```text
.claude/commands/query-export.md
```

命令说明（示意）：

```markdown
---
description: 执行 SQL 查询并将结果导出为 CSV 或 JSON
argument-hint: <dbName> <csv|json> <sql...>
---

你是 db_query 导出助手。请按以下步骤执行，不要跳过：

1. 确认后端可用：GET http://localhost:8000/health
2. 解析用户参数：$ARGUMENTS
   - 第 1 个词：数据库连接名
   - 第 2 个词：格式 csv 或 json
   - 其余：SQL 语句
3. 调用脚本（优先）或直接用 curl + 本地转换：
   `uv run python scripts/query_export.py --db ... --format ... --sql "..."`
4. 向用户报告：行数、耗时（若有）、导出文件绝对路径
5. 若失败：打印 API 错误 detail，并给出修复建议（连接是否存在、是否非 SELECT 等）
```

使用方式（对话中）：

```text
/query-export postgres csv SELECT current_user, now()
```

### 3.5 Agent 行为约束

- **只读**：脚本层复用后端「仅 SELECT」校验，禁止写操作导出  
- **路径沙箱**：默认只写项目下 `exports/`（可加入 `.gitignore`）  
- **密钥**：不把数据库密码写进命令参数；依赖后端已保存的连接  
- **幂等命名**：文件名带时间戳，避免覆盖  

### 3.6 验收标准

- [ ] 一条命令可完成查询 + 落盘  
- [ ] CSV / JSON 均可指定  
- [ ] 失败时有可读错误，不静默成功  
- [ ] Claude Code 中 `/query-export` 文档可被 Agent 按步骤执行  

---

## 4. 功能三：用户交互（自然语言 / 界面触发导出）

### 4.1 交互目标

降低「查完还要找导出按钮」的摩擦，形成：

**查询完成 → 主动确认 → 一键导出** 的闭环。

### 4.2 方案 A：查询成功后的主动询问（推荐首期）

在 `EXECUTE` 成功且 `rowCount > 0` 时，弹出轻量确认（不打断重度用户时可配置关闭）：

```text
查询完成，共 42 行。
需要将本次结果导出吗？

[ 导出 CSV ]  [ 导出 JSON ]  [ 不用了 ]
```

实现要点：

- 使用 Ant Design `Modal` 或结果区顶部的 `Alert` + 操作按钮  
- 记住用户偏好：`localStorage.exportPrompt = 'always' | 'never' | 'ask'`  
- 与现有 `EXPORT CSV/JSON` 按钮并存（按钮仍是显式入口）

### 4.3 方案 B：自然语言指令导出

在现有 **NATURAL LANGUAGE** 能力上扩展「意图识别」两类意图：

| 用户说法 | 意图 | 行为 |
|----------|------|------|
| 「查询所有活跃用户」 | `query` | 生成 SQL →（可选）自动执行 |
| 「把刚才的结果导出成 CSV」 | `export` | 对当前 `queryResult` 调用导出 |
| 「查当前库名并导出为 JSON」 | `query_and_export` | 生成 → 执行 → 导出 |

前端伪流程：

```text
用户 prompt
  → 先做轻量意图分类（规则或小模型）
  → export：直接导出，不调 NL2SQL
  → query：走现有 /query/natural
  → query_and_export：natural → execute → export(format)
```

规则示例（零成本先做）：

- 含「导出」「download」「export」且含 `csv|json|excel` → export / query_and_export  
- 仅「导出」且无格式 → 弹出格式选择  

### 4.4 方案 C：结果区 AI 助手气泡（增强）

查询成功后，在 Results 卡片显示助手提示条：

> AI：需要将这次查询结果导出为 **CSV** 或 **JSON** 文件吗？

点击对应链接即触发导出；关闭后本会话不再提示。

这与方案 A 同类，视觉上更「助手化」，适合课程演示。

### 4.5 推荐落地顺序

1. **P0**：保持并巩固现有双按钮导出（已具备）  
2. **P1**：查询成功后主动询问（方案 A / C）  
3. **P1**：CLI + `.claude/commands/query-export.md`（自动化）  
4. **P2**：自然语言「导出 / 查询并导出」意图（方案 B）  

---

## 5. 整体架构示意

```text
┌─────────────────────────────────────────────────────────┐
│  UI (Home)                                              │
│  - EXECUTE → queryResult                                │
│  - EXPORT CSV / JSON（现有）                            │
│  - 查询后询问条 / NL「导出」意图（新增）                  │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP
┌───────────────────────▼─────────────────────────────────┐
│  Backend                                                │
│  POST /api/v1/dbs/{name}/query                           │
│  （可选）POST /export                                   │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│  Automation                                             │
│  scripts/query_export.py  ←──  .claude/commands/…       │
│  写文件到 exports/                                      │
└─────────────────────────────────────────────────────────┘
```

---

## 6. 安全与体验注意点

| 点 | 处理 |
|----|------|
| 仅允许 SELECT | 沿用后端 sqlglot 校验；自动化脚本不绕过 API |
| 大结果内存 | 前端 >10000 行确认；CLI 可加重试/流式（后期） |
| 敏感数据 | 导出文件本地保存，提示勿提交仓库；`exports/` 进 `.gitignore` |
| 密码 | 自动化只用已注册连接名，不在命令行传 DB 密码 |
| 中文 Excel | CSV 可选 BOM |

---

## 7. 建议目录与文件变更清单

| 路径 | 动作 | 说明 |
|------|------|------|
| `frontend/src/utils/exportResults.ts` | 新增 | 抽离导出逻辑 |
| `frontend/src/pages/Home.tsx` | 修改 | 查询后询问、复用 utils |
| `frontend/src/components/ExportPrompt.tsx` | 新增 | 主动询问条（可选） |
| `scripts/query_export.py` | 新增 | 一键查询+导出 CLI |
| `exports/.gitkeep` | 新增 | 导出目录占位 |
| `.gitignore` | 修改 | 忽略 `exports/*` |
| `.claude/commands/query-export.md` | 新增 | Claude Code 命令 |
| `FEATURE_EXPORT.md` | 本文件 | 设计说明 |

---

## 8. 演示话术（课程/验收可用）

1. 页面执行：`SELECT current_database(), now();` → 点 **EXPORT CSV** / **EXPORT JSON**，打开文件核对。  
2. 查询成功后弹出：「需要导出为 CSV 或 JSON 吗？」→ 点格式完成下载。  
3. 终端或 Claude Code：

```text
/query-export postgres json SELECT current_user AS user, now() AS ts
```

展示生成的 `exports/*.json`。

---

## 9. 总结

- **格式**：CSV + JSON 双格式是当前与后续的最小完备集；前端 Blob 导出已覆盖核心需求。  
- **自动化**：用「API 查询 + 本地序列化」脚本，配合 Claude Code Command，实现真正的一键「执行+导出」，比操控浏览器更可靠。  
- **交互**：查询后主动询问 + 自然语言导出意图，把导出从「找按钮」变成「对话/确认」式体验。  

## 10. 实现状态（已落地）

下列项已在代码中实现，可直接验证：

| 项 | 位置 |
|----|------|
| CSV / JSON 导出工具（含 UTF-8 BOM） | `frontend/src/utils/exportResults.ts` |
| 导出意图解析 | `frontend/src/utils/exportIntent.ts` |
| 查询后主动询问 | `frontend/src/components/ExportPrompt.tsx` + `Home.tsx` |
| 自然语言导出 / 查询并导出 | `Home.tsx` → `handleGenerateSQL` |
| 一键 CLI | `scripts/query_export.py` |
| 导出目录 | `exports/`（数据文件 gitignore） |
| Claude Code 命令 | `.claude/commands/query-export.md` |

### 快速验证

```powershell
# 后端需已启动，且 UI 中已添加名为 postgres 的连接
python scripts/query_export.py --db postgres --format csv --sql "SELECT now() AS ts"
```

页面：执行 SELECT → 结果区出现导出询问 → 或点 EXPORT CSV/JSON；自然语言输入「把刚才的结果导出成 CSV」。
