# DB Query Tool — 功能清单与测试指南

本文档基于当前代码实现整理，说明已实现功能及推荐测试方法。

---

## 一、已实现功能清单

### 1. 基础设施

| 功能 | 说明 | UI | API |
|------|------|----|-----|
| 健康检查 | 确认后端存活 | 无 | `GET /health` |
| 本地持久化 | 连接/元数据缓存/查询历史存 SQLite（`~/.db_query/db_query.db`） | — | — |
| CORS | 可配置跨域来源 | — | — |
| 多数据库适配 | PostgreSQL、MySQL | URL 自动识别 | — |

### 2. 数据库连接管理

| 功能 | 说明 | UI | API |
|------|------|----|-----|
| 添加/更新连接 | 名称 + URL（可选描述）；保存前测试连通性 | 侧边栏「ADD DATABASE」 | `PUT /api/v1/dbs/{name}` |
| 列出连接 | 名称、URL、类型、状态等 | 左侧连接列表 | `GET /api/v1/dbs` |
| 删除连接 | 关闭连接池并删除记录 | 侧边栏删除确认 | `DELETE /api/v1/dbs/{name}` |
| URL 类型检测 | `postgresql://` / `mysql://` 等 | 前端校验 + 后端检测 | 内置于 PUT |
| 连接状态 | active / inactive / error | 列表图标颜色 | GET 响应字段 |

支持的 URL 示例：

```text
postgresql://user:password@localhost:5432/dbname
mysql://user:password@localhost:3306/dbname
```

### 3. 元数据浏览

| 功能 | 说明 | UI | API |
|------|------|----|-----|
| 获取 schema | 表/视图、列名、类型、可空、主键等 | 选中库后自动加载 | `GET /api/v1/dbs/{name}` |
| 元数据缓存 | SQLite 缓存，默认 24 小时有效 | — | GET 命中缓存 |
| 强制刷新 | 重新从目标库拉取 | 「REFRESH」按钮 | `POST /api/v1/dbs/{name}/refresh` |
| 树形浏览 | Tables / Views 分组，列级信息 | MetadataTree | — |
| 搜索过滤 | 按表名、列名过滤 | 搜索框 | — |
| 点击表生成 SQL | 填充 `SELECT * FROM ... LIMIT 100` | 点击树节点 | — |
| 统计指标 | 表数量、视图数量 | 顶部指标卡片 | — |

### 4. SQL 查询执行

| 功能 | 说明 | UI | API |
|------|------|----|-----|
| 执行 SELECT | 返回列、行、行数、耗时 | Monaco 编辑器 + EXECUTE | `POST /api/v1/dbs/{name}/query` |
| 仅允许 SELECT | INSERT/UPDATE/DELETE 等会被拒绝 | 错误提示 | sqlglot 校验 |
| 自动 LIMIT | 无 LIMIT 时自动加 `LIMIT 1000` | — | 内置于查询 |
| 方言感知 | PostgreSQL / MySQL 分别校验 | — | 内置 |
| 结果表格 | 分页展示（10/20/50/100） | Results 区域 | — |
| 执行指标 | 行数、耗时 | 指标卡片 | 响应字段 |

### 5. 自然语言转 SQL（NL2SQL）

| 功能 | 说明 | UI | API |
|------|------|----|-----|
| 自然语言生成 SQL | 基于 schema 上下文，调用 OpenAI | NATURAL LANGUAGE 页签 | `POST /api/v1/dbs/{name}/query/natural` |
| 中英文支持 | prompt 支持中文/英文 | 输入框 | — |
| 返回 SQL + 说明 | `{ sql, explanation }` | 生成后填入编辑器 | 响应字段 |
| 仅生成不执行 | 需用户再点 EXECUTE | 自动切到 MANUAL SQL | — |
| 快捷键 | Cmd/Ctrl + Enter 生成 | NaturalLanguageInput | — |

**依赖：** `backend/.env` 中配置真实 `OPENAI_API_KEY`，且该库已有元数据。

### 6. 查询历史

| 功能 | 说明 | UI | API |
|------|------|----|-----|
| 自动记录 | 每次执行（成功/失败）写入 SQLite | **当前主界面未展示** | 内部 |
| 查询历史列表 | 最近 N 条，默认 50，每库最多保留 50 | **当前主界面未展示** | `GET /api/v1/dbs/{name}/history` |

> 历史 API 已实现，可通过 REST Client / curl / Swagger 验证；主页 `Home.tsx` 尚未接入历史面板。

### 7. 结果导出（纯前端）

| 功能 | 说明 | UI | API |
|------|------|----|-----|
| 导出 CSV | RFC 4180 转义 | EXPORT CSV | 无（浏览器下载） |
| 导出 JSON | 美化 JSON | EXPORT JSON | 无 |
| 大数据警告 | 超过 10000 行弹窗确认 | Modal | — |
| 空结果保护 | 无数据时提示 | warning | — |

### 8. 已知限制 / 未挂载能力

- 主 UI 无「查询历史」面板（API 可用）
- 无独立「编辑连接」表单（可用同名 PUT 覆盖）
- Refine 旧页面（`pages/databases/*`、`pages/queries/execute.tsx`）存在但未挂载路由
- 应用自身不需要安装 PostgreSQL/MySQL；**完整业务测试**需要至少一个目标库

---

## 二、测试前准备

### 1. 启动服务

确保前后端已启动：

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

若未启动（Windows 无 make 时可手动）：

```powershell
# 后端
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端（需 Node 20+，本机可用 C:\Program Files\nodejs）
cd frontend
npm run dev
```

### 2. 准备目标数据库（二选一）

| 类型 | 用途 |
|------|------|
| PostgreSQL | 与 `fixtures/test.rest` 默认示例一致 |
| MySQL | 可用 `backend/scripts/` 面试示例库 |

至少准备一个可连通的库，并记下连接 URL。

可选：初始化 MySQL 面试示例库（见 `backend/scripts/INTERVIEW_DB_README.md`）：

```bash
# 在能访问 mysql 客户端的环境中
mysql -u root < create_interview_db.sql
mysql -u root < seed_interview_data.sql
# ... part2 / part3 按 README
```

### 3. 自然语言功能（可选）

编辑 `backend/.env`：

```env
OPENAI_API_KEY=sk-你的真实密钥
```

修改后需重启后端。

### 4. 修改测试变量

打开 `fixtures/test.rest`，按实际环境修改：

```text
@baseUrl = http://localhost:8000/api/v1
@dbName = todo
@testDbUrl = postgresql://postgres:postgres@localhost:5432/{{dbName}}
```

MySQL 示例：

```text
@testDbUrl = mysql://root:password@localhost:3306/interview_db
```

---

## 三、测试方法总览

| 层级 | 方法 | 覆盖范围 | 是否需要目标库 |
|------|------|----------|----------------|
| A. 冒烟 | 浏览器 / curl | 服务是否启动 | 否 |
| B. 单元测试 | `pytest` | 后端核心逻辑 | 否（内存 SQLite） |
| C. API 测试 | REST Client / Swagger | 全量后端接口 | 是（多数用例） |
| D. UI 验收 | 浏览器操作 | 前端主流程 | 是 |

---

## 四、A. 冒烟测试

```powershell
Invoke-RestMethod http://localhost:8000/health
# 期望: status = healthy

# 浏览器打开
# http://localhost:5173
# http://localhost:8000/docs
```

| 步骤 | 预期 |
|------|------|
| 访问 `/health` | `{"status":"healthy","version":"1.0.0"}` |
| 打开前端 | 页面加载，可见侧边栏与主区域 |
| 打开 `/docs` | Swagger 可交互 |

---

## 五、B. 自动化单元测试

```powershell
cd backend
uv run pytest -v
```

覆盖模块示例：

- `test_api_databases.py` — 连接 CRUD
- `test_api_queries.py` — 查询 API
- `test_metadata.py` — 元数据
- `test_query.py` — 查询逻辑
- `test_sql_validator.py` — SQL 校验 / LIMIT
- `test_nl2sql.py` — NL2SQL（可能 mock）

**通过标准：** 全部用例绿色。失败时根据报错定位对应服务。

---

## 六、C. API 测试（推荐用 REST Client）

### 工具

1. 安装 VS Code / Cursor 扩展：[REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
2. 打开 `fixtures/test.rest`
3. 在请求上方点击 **Send Request**

也可使用 http://localhost:8000/docs 在线调试。

### 建议执行顺序与预期

| # | 场景 | 请求 | 预期结果 |
|---|------|------|----------|
| 0 | Health | `GET /health` | 200，healthy |
| 1 | 列出连接 | `GET /api/v1/dbs` | 200，数组 |
| 2 | 创建连接 | `PUT /api/v1/dbs/{name}` + url | 200，返回连接信息；错误 URL 应 4xx |
| 3 | 获取元数据 | `GET /api/v1/dbs/{name}` | 200，含 tables/views |
| 4 | 刷新元数据 | `POST /api/v1/dbs/{name}/refresh` | 200，元数据更新 |
| 5 | 简单 SELECT | `POST .../query` `SELECT 1` 或查已有表 | 200，有 columns/rows |
| 6 | 无 LIMIT 的 SELECT | `SELECT * FROM ...` | 自动 LIMIT 1000，正常返回 |
| 7 | 非法写操作 | `INSERT ...` | 400，仅允许 SELECT |
| 8 | 语法/列错误 | 错误 SQL | 4xx/5xx，有错误信息 |
| 9 | NL2SQL（需 Key） | `POST .../query/natural` | 200，含 sql、explanation |
| 10 | 查询历史 | `GET .../history` | 200，含此前执行记录 |
| 11 | 删除连接 | `DELETE /api/v1/dbs/{name}` | 200/204；再 GET 应 404 |

### curl 示例（PowerShell）

```powershell
# 健康检查
Invoke-RestMethod http://localhost:8000/health

# 创建连接（按实际 URL 修改）
Invoke-RestMethod -Method Put `
  -Uri "http://localhost:8000/api/v1/dbs/demo" `
  -ContentType "application/json" `
  -Body '{"url":"postgresql://postgres:postgres@localhost:5432/postgres","description":"local demo"}'

# 获取元数据
Invoke-RestMethod http://localhost:8000/api/v1/dbs/demo

# 执行查询
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/v1/dbs/demo/query" `
  -ContentType "application/json" `
  -Body '{"sql":"SELECT 1 AS n"}'

# 自然语言（需有效 OPENAI_API_KEY）
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/v1/dbs/demo/query/natural" `
  -ContentType "application/json" `
  -Body '{"prompt":"查询当前时间"}'

# 历史
Invoke-RestMethod "http://localhost:8000/api/v1/dbs/demo/history?limit=10"
```

---

## 七、D. 前端 UI 验收清单

打开 http://localhost:5173，按表逐项勾选。

### 1. 连接管理

| 用例 | 操作 | 预期 |
|------|------|------|
| 添加成功 | ADD DATABASE，填名称与合法 URL，保存 | 列表出现该连接，状态正常 |
| 添加失败 | 使用错误密码/不可达主机 | 提示错误，不进入正常列表状态 |
| 切换连接 | 点击列表中另一连接 | Schema 区域切换到对应库 |
| 删除连接 | 删除确认 | 列表移除，相关视图清空 |

### 2. 元数据

| 用例 | 操作 | 预期 |
|------|------|------|
| 自动加载 | 选中已连接库 | 显示 Tables/Views 树 |
| 搜索 | 输入表名/列名关键字 | 树过滤结果正确 |
| 点击表 | 点击某表节点 | SQL 编辑器填入 SELECT 模板 |
| 刷新 | 点 REFRESH | 元数据重新加载，无报错 |
| 指标 | 查看顶部卡片 | 表数/视图数与树一致 |

### 3. 手写 SQL

| 用例 | 操作 | 预期 |
|------|------|------|
| 正常查询 | 执行合法 SELECT | Results 有数据，显示行数与耗时 |
| 自动 LIMIT | 无 LIMIT 的大表查询 | 最多约 1000 行 |
| 拒绝写操作 | 执行 INSERT/UPDATE/DELETE | 明确错误提示 |
| 语法错误 | 故意写错 SQL | 错误提示可读 |
| 分页 | 切换 pageSize | 表格分页正常 |

### 4. 自然语言转 SQL

| 用例 | 操作 | 预期 |
|------|------|------|
| 未配置 Key | 未改 `.env` 或 Key 无效 | 有错误提示 |
| 中文生成 | 输入「查询所有…」并生成 | 得到 SQL，切到 MANUAL SQL |
| 英文生成 | 输入英文 prompt | 同上 |
| 再执行 | 对生成 SQL 点 EXECUTE | 结果正确（或可编辑后执行） |
| 快捷键 | Ctrl+Enter | 触发生成 |

### 5. 导出

| 用例 | 操作 | 预期 |
|------|------|------|
| 无结果导出 | 无查询结果时点导出 | warning，不下载 |
| CSV | 有结果时 EXPORT CSV | 下载 `{db}_{timestamp}.csv`，可用 Excel 打开 |
| JSON | EXPORT JSON | 下载合法 JSON 数组文件 |
| 超大数据 | 结果 >10000 行时导出 | 出现确认弹窗 |

### 6. 查询历史（API 验证）

主界面暂无历史面板，请用 API 验证：

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/dbs/demo/history?limit=10"
```

预期：包含刚才 UI/API 执行过的 SQL、成功/失败、耗时、行数等字段。

---

## 八、推荐测试路径（最短闭环）

1. **冒烟**：`/health` + 打开前端  
2. **单元测试**：`uv run pytest -v`  
3. **接库**：安装 PostgreSQL 或 MySQL，改 `test.rest` 中的 URL  
4. **API 闭环**：创建连接 → 元数据 → SELECT →（可选）NL2SQL → history → 删除  
5. **UI 闭环**：同样流程在浏览器走一遍，并测导出  

---

## 九、常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 前端空白/依赖报错 | Node 版本过旧（需 20+） | 使用 Node 24：`nvm use 24` 或 `C:\Program Files\nodejs` |
| 创建连接失败 | 目标库未启动/账号错误/防火墙 | 用客户端先验证 URL |
| 元数据为空 | 库无表或权限不足 | 换有表的库，或检查用户权限 |
| NL2SQL 失败 | Key 无效或未重启后端 | 检查 `.env` 并重启 uvicorn |
| INSERT 被拒 | 设计如此，只读查询 | 改用 SELECT |
| 历史 UI 看不到 | Home 未接入 | 用 `/history` API 验证 |

---

## 十、相关文件

| 文件 | 说明 |
|------|------|
| `fixtures/test.rest` | API 请求合集 |
| `fixtures/README.md` | REST Client 使用说明 |
| `backend/scripts/INTERVIEW_DB_README.md` | MySQL 示例库说明 |
| `PHASE3_IMPLEMENTATION.md` | NL / 导出等 Phase 3 实现说明 |
| `backend/.env.example` | 环境变量模板 |
| `http://localhost:8000/docs` | 在线 API 文档 |
