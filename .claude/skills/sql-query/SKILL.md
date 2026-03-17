---
name: sql-query
description: "在美团 魔数BI 平台（bi.sankuai.com）执行 SQL 查询并获取结果。通过 mtdata bi CLI 调用后端 API，支持工作空间/队列选择、SQL 提交、状态轮询、结果获取。当用户提到在 魔数BI 平台查数据、执行 SQL 查询、跑 SQL、查 Hive/MySQL/Doris 数据时使用。"
---
# BI SQL 查询（mtdata bi）

通过 `mtdata bi` 命令在 bi.sankuai.com 上执行 SQL 查询并获取结果。自动处理美团内网 SSO，大多数环境用户无感**无需打开浏览器窗口**。

> **境外网络说明**：如果用户在境外（海外）网络环境，`bi.sankuai.com` 可能无法访问，此时需要将域名换成 `bi.keetapp.com`（即 `sankuai` → `keetapp`），所有命令通过 `--base-url https://bi.keetapp.com` 参数传入。

## 执行流程概览

```
Step 1: 询问数据源类型（Hive / Doris / MySQL）
  ↓
Step 2: 并行获取工作空间列表 + 数据源列表（后台静默执行）
  ↓
Step 3: 执行 SQL
  - Hive：直接执行，--queue 可省略（自动选最优队列）
  - Doris/MySQL：自动选唯一数据源，多个时选第一个有权限的
  ↓
Step 4: 展示查询结果
```

**核心原则：最小化用户交互。除数据源类型外，其余参数均自动推断，无需用户确认。**

---

## AI 使用提示

**重要原则：遇到问题不要猜测，优先使用 `--help` 自行探索**

当遇到不熟悉的命令或参数时，AI 应该：

1. 首先尝试使用 `mtdata bi --help` 查看主命令帮助
2. 对于子命令，使用 `mtdata bi <command> --help` 查看具体用法
3. 根据帮助文档的指引进行下一步操作
4. 只有在帮助文档无法解决问题时，才参考本技能文档的其他部分

这能确保 AI 始终基于最新的命令语法和参数进行操作，避免因猜测导致的错误。

---

## 安装与更新

> 在使用前请检查是否为最新版本，首次使用请完整执行初始化流程

```bash
uv tool install --upgrade --index-url https://pypi.sankuai.com/simple/ mt-data-cli
```

**沙箱环境（类 OpenClaw）** `~/.local/` 非持久化，需指定持久化路径：

```bash
export UV_TOOL_DIR="/mnt/openclaw/.uv-tools"
export UV_TOOL_BIN_DIR="/mnt/openclaw/.uv-tools/bin"
uv tool install --upgrade --index-url https://pypi.sankuai.com/simple/ mt-data-cli
ln -sf /mnt/openclaw/.uv-tools/bin/mtdata /root/.local/bin/mtdata
```

> 跨平台通用（macOS / Linux / Windows）。需先安装 Python 3.10+ 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)；安装遇到问题见 [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)。

验证：`mtdata --help` 正常输出即可。

---

# SSO 认证

mtdata 自动处理美团内网 SSO，大多数环境用户无感。遇到认证问题时按环境处理：

- **标准开发机**：用 Chrome 打开美团内网并登录即可。
- **沙箱环境（CatClaw）**：安装后运行 `bash <skill_base_dir>/scripts/setup-sandbox.sh` 初始化 CDP 配置（自动检测，非沙箱跳过）。确保 MOA 已登录，认证失败时触发 moa-login skill。**注意：此脚本仅适用于沙箱环境，勿在 CatPaw Desk 中使用。**
- **桌面 AI 工具（类 CatDesk）**：
  
  **主方案（脚本注入）**：运行注入脚本将 CatPaw 的 SSO 状态写入 mtdata 缓存。

  **macOS / Linux：**

  ```bash
  python3 <skill_base_dir>/scripts/sso-inject.py            # 注入 SSO
  python3 <skill_base_dir>/scripts/sso-inject.py --check    # 仅查看缓存状态
  ```

  **Windows PowerShell：**

  ```powershell
  python <skill_base_dir>\\scripts\\sso-inject.py            # 注入 SSO
  python <skill_base_dir>\\scripts\\sso-inject.py --check    # 仅查看缓存状态
  ```

  SSO 过期后重新运行即可。前提：CatPaw Desk 已登录美团内网。

  **备用方案（浏览器 Cookie）**：如果脚本注入失败，mtdata 会自动尝试从系统浏览器的 Cookie 存储中读取 bi_ssoid。确保 Chrome/Edge/Arc 浏览器已登录 bi.sankuai.com，整个过程用户零感知，无需手动操作。

> 详细排查见 [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)。

---

## Step 0: 确认网络环境（境外用户）

**如果用户明确说明在境外，或后续步骤出现连接失败**，应询问用户是否切换到境外域名：

```
AI: 检测到访问 bi.sankuai.com 失败，错误信息：<原始错误>
    您是否在境外网络环境？如果是，我将切换到境外域名 bi.keetapp.com 重试。
    请确认：是 / 否
```

用户确认后，所有后续命令统一附加 `--base-url https://bi.keetapp.com`。

---

## Step 1: 询问数据源类型（唯一必要的用户交互）

**这是整个流程中唯一需要用户选择的步骤。** 使用 `AskQuestion` 工具询问：

```
AskQuestion:
  title: "查询配置"
  questions:
    - id: "datasource_type"
      prompt: "请选择数据源类型："
      input_type: "choice"
      options:
        - id: "hive"
          label: "Hive/OneSQL（数仓表）"
        - id: "doris"
          label: "Doris（实时表）"
        - id: "mysql"
          label: "MySQL（关系型数据库）"
```

> **注意**：如果用户在提问时已经明确说明了数据源类型（如"查 Hive 数据"、"查实时表"），则跳过此步骤，直接进入 Step 2。

---

## Step 2: 后台静默获取配置信息

用户选择数据源类型后，**无需等待用户确认**，立即后台执行以下命令获取所需信息：

```bash
# 获取工作空间列表（所有类型都需要）
mtdata bi spaces

# Doris/MySQL 还需要获取数据源列表
mtdata bi datasources
```

**工作空间自动选择规则：**

- 如果只有个人空间（ID=0），直接使用，不询问用户。
- 如果有多个工作空间，**默认使用个人空间（ID=0）**，不询问用户。
- 只有当用户明确提到某个项目组名称时，才使用对应的项目组空间。

**数据源自动选择规则（Doris/MySQL）：**

- 筛选出对应引擎类型的数据源（有 ✅ 权限的）。
- 如果只有 1 个，直接使用，不询问用户。
- 如果有多个，**自动选择第一个有权限的数据源**，不询问用户。
- 如果无对应数据源：告知用户无法执行查询，停止。

---

## Step 3: 执行 SQL

### Hive/OneSQL 查询

`--queue` 参数**可以省略**，工具会自动选择有配额的最优队列：

```bash
# 个人空间（推荐写法，省略 --queue 和 --project）
mtdata bi run "<USER_SQL>"

# 指定项目组空间
mtdata bi run "<USER_SQL>" --project <PROJECT_ID>

# 境外环境
mtdata bi run "<USER_SQL>" --base-url https://bi.keetapp.com
```

### Doris 查询

```bash
# 个人空间
mtdata bi run "<USER_SQL>" --engine doris --ds <DORIS_DSN> --stat-ds <DORIS_STAT_DS>

# 指定项目组空间
mtdata bi run "<USER_SQL>" --project <PROJECT_ID> --engine doris --ds <DORIS_DSN> --stat-ds <DORIS_STAT_DS>

# 境外环境
mtdata bi run "<USER_SQL>" --engine doris --ds <DORIS_DSN> --stat-ds <DORIS_STAT_DS> --base-url https://bi.keetapp.com
```

### MySQL 查询

```bash
# 个人空间
mtdata bi run "<USER_SQL>" --engine mysql --ds <MYSQL_DSN> --stat-ds <MYSQL_STAT_DS>

# 指定项目组空间
mtdata bi run "<USER_SQL>" --project <PROJECT_ID> --engine mysql --ds <MYSQL_DSN> --stat-ds <MYSQL_STAT_DS>

# 境外环境
mtdata bi run "<USER_SQL>" --engine mysql --ds <MYSQL_DSN> --stat-ds <MYSQL_STAT_DS> --base-url https://bi.keetapp.com
```

`mtdata bi run` 内部自动完成：预分析 → 提交 → 轮询（最多 3 分钟）→ 取结果。

---

## Step 4: 展示结果

命令成功后，以表格形式展示查询结果，并说明总行数是否被截断。

---

## 参数说明

### `mtdata bi run` 常用参数

| 参数                   | 默认值                       | 说明                                                                 |
| ---------------------- | ---------------------------- | -------------------------------------------------------------------- |
| `<USER_SQL>`         | 必填                         | 要执行的 SQL 语句                                                    |
| `--project` / `-p` | `0`                        | 工作空间 ID，0=个人空间，其他为项目组 ID                             |
| `--queue` / `-q`   | 自动选择                     | Spark 队列名，**可省略**，工具自动选择有配额的队列             |
| `--engine` / `-e`  | `onesql`                   | 查询引擎：`onesql` / `hive` / `presto` / `doris` / `mysql` |
| `--ds`               | `dw_hive`                  | 数据源名称，需与 `--engine` 和 `--stat-ds` 匹配                  |
| `--stat-ds`          | `DW_ONESQL_DB_CONNECT_URL` | 数据源连接标识                                                       |
| `--resource-name`    | `新查询`                   | 查询名称，在 BI 平台中展示                                           |
| `--limit` / `-n`   | `200`                      | 返回结果行数上限（仅 `run`）                                       |
| `--timeout` / `-t` | `180`                      | 最长等待秒数（仅 `run`）                                           |
| `--base-url`         | `https://bi.sankuai.com`   | BI 平台地址；**境外用户请传 `https://bi.keetapp.com`**       |

### 引擎/数据源配套说明

**重要**：`--engine` / `--ds` / `--stat-ds` 三个参数需配套使用。

| 引擎类型            | `--engine` | `--ds`        | `--stat-ds`                 | 说明           |
| ------------------- | ------------ | --------------- | ----------------------------- | -------------- |
| HIVE/ONESQL（默认） | `onesql`   | `dw_hive`     | `DW_ONESQL_DB_CONNECT_URL`  | 数仓查询       |
| DORIS               | `doris`    | `<doris_dsn>` | `<DORIS连接URL>`            | Doris 实时数仓 |
| MYSQL               | `mysql`    | `mysqldw`     | `DW_MYSQL_DB_CONNECT_URL`   | MySQL 数据仓库 |
| MYSQL（测试环境）   | `mysql`    | `mysqldwtest` | `ETLTEST_DW_DB_CONNECT_URL` | MySQL 测试环境 |

**查看可用数据源**：`mtdata bi datasources`

---

## 能力矩阵

| 目标             | 命令                                       |
| ---------------- | ------------------------------------------ |
| 查看可用工作空间 | `mtdata bi spaces`                       |
| 查看可用队列     | `mtdata bi queues`                       |
| 查看可用数据源   | `mtdata bi datasources [--project <id>]` |
| 一键执行 SQL     | `mtdata bi run "<SQL>"`                  |
| 仅提交（异步）   | `mtdata bi submit "<SQL>"`               |
| 查询执行状态     | `mtdata bi status <queryId>`             |
| 获取已完成结果   | `mtdata bi result <queryId>`             |

---

## 长时间 SQL 执行处理策略

### 策略一：增加超时时间

```bash
# 增加查询超时时间（默认180秒，可增加到600秒=10分钟）
mtdata bi run "<LONG_SQL>" --timeout 600

# 超大查询可设置更长时间
mtdata bi run "<VERY_LONG_SQL>" --timeout 1800  # 30分钟
```

### 策略二：异步执行 + 轮询结果（推荐）

```bash
# 1. 仅提交查询（异步执行，立即返回queryId）
queryId=$(mtdata bi submit "<LONG_SQL>" --resource-name "长时间查询任务")

echo "查询已提交，Query ID: $queryId"

# 2. 轮询查询状态
mtdata bi status "$queryId"

# 3. 获取结果（当状态为SUCCESS时）
mtdata bi result "$queryId" --limit 1000
```

### 策略三：分批查询 + 结果合并

```bash
# 按时间范围分批查询
mtdata bi run "SELECT * FROM large_table WHERE dt='2026-03-01'"
mtdata bi run "SELECT * FROM large_table WHERE dt='2026-03-02'"
mtdata bi run "SELECT * FROM large_table WHERE dt='2026-03-03'"
```

### 策略四：优化查询性能

```bash
# 添加合适的LIMIT限制
mtdata bi run "SELECT * FROM large_table LIMIT 10000"

# 使用分区字段过滤
mtdata bi run "SELECT * FROM large_table WHERE dt>=CURRENT_DATE()-7"

# 只选择必要字段
mtdata bi run "SELECT col1, col2, col3 FROM large_table"
```

> **Agent 探索建议**：
>
> - 对于预期执行时间超过5分钟的查询，优先使用异步执行
> - 可以通过 `--timeout` 参数灵活调整等待时间
> - 大结果集查询时，适当增加 `--limit` 参数获取更多数据
> - 考虑使用分区字段和WHERE条件减少数据扫描量

---

## 注意事项

- `--queue` 参数现在**可以省略**，工具会自动选择有配额的最优队列；只有用户明确指定队列时才传入
- `--project` 参数处理：个人空间（ID为0）可不传此参数使用默认值，项目组空间必须传入对应的项目组ID
- **Doris/MySQL 查询**：不需要 `--queue` 参数，但需要指定 `--engine`、`--ds` 和 `--stat-ds` 参数
- 大查询可能需要较长轮询时间，`--timeout` 默认 180 秒（3 分钟），可增加到 600-1800 秒
- 结果超过 `--limit` 行时会提示截断，可增大 `--limit` 或使用 `LIMIT` 限制 SQL
- **长时间查询建议**：预期执行超过 5 分钟的查询，优先使用异步执行（`mtdata bi submit` + `mtdata bi result`）
- 认证失败时，确保已在本地浏览器（Chrome/Edge/Arc）登录对应域名的 BI 平台
- **境外网络**：`sankuai.com` 域名在境外不可达，此时必须改用 `keetapp.com` 域名

  - 失败错误中含 `connection`、`timeout`、`resolve` 等关键词时，主动询问用户是否在境外
  - 用户确认后，本次会话后续所有命令均附加 `--base-url https://bi.keetapp.com`
- **找数找表**：如果不明确用户的查询内容，使用 `mtdata --help`自行探索相应能力。

---

### 验证安装

```bash
mtdata bi --help
```
