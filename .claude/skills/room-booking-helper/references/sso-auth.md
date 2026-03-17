# SSO 认证架构详解

所有接口在 `calendar.sankuai.com` 域名下，需要美团 SSO 登录态。根据运行环境自动选择最优认证方式。

## 环境检测与认证策略

首先通过脚本检测当前运行环境：

```bash
python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py check-env
```

认证策略优先级（由 `detect_auth_strategy()` 决定）：

| 优先级 | 策略 | 触发条件 | 说明 |
|--------|------|----------|------|
| 1 | `catpaw_exchange` | `~/.catpaw/sso_config.json` 存在 | CatPaw Desk 换票方案（**首选**） |
| 2 | `ciba` | sso_config.json 不存在 + `IDENTIFIER` 环境变量或 sandbox.json 存在 | CIBA 大象授权（Sandbox 环境） |
| 3 | `browser` | 以上均不满足 | 浏览器 fetch 降级 / 读取 cookie.json |

## 文件结构

```
~/.catpaw/skills/room-booking-helper/
├── SKILL.md                    # 主文档
├── cookie.json                 # SSO cookie（仅 Sandbox/CIBA 流程自动生成）
├── scripts/
│   ├── rbh_sso.py              # SSO 认证主脚本（新版，推荐）
│   ├── sso-login.sh            # 旧版 CIBA bash 脚本（兼容保留）
│   └── inject-cookie.py        # 旧版 CDP 注入脚本（兼容保留）
└── resources/
    └── quick_book.py           # 快速预订脚本（已内置三策略认证）

~/.catpaw/
└── sso_config.json             # CatPaw 统一 SSO 配置（本地环境身份标识来源）
```

## 策略 1：CatPaw Desk 换票方案（本地环境首选）

当 `~/.catpaw/sso_config.json` 存在时自动触发。

**步骤**：读取 `sso_config.json` 中的 `ssoid` → 调换票接口换取 `calendar.sankuai.com` 专属 token → 以 `calendar_ssoid=<token>` 格式作为 Cookie 使用。

无需任何手动操作，`quick_book.py` 和 `rbh_sso.py load-cookie` 均自动完成。

## 策略 2：CIBA 大象授权（Sandbox 环境）

当 `sso_config.json` 不存在且检测到 Sandbox 环境时触发。

### 一键登录（推荐）

```bash
python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py ciba-login <misId>

# 示例
python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py ciba-login wangjun137
```

### 流程

1. 发起 CIBA 认证 → 用户在大象上收到授权确认请求
2. 用户点击确认 → 系统自动获取 access_token
3. 换票 → 用 access_token 换取 calendar.sankuai.com 的 Cookie
4. 保存到 `cookie.json` → 供后续 `quick_book.py` 使用

## 策略 3：浏览器 fetch 降级（本地兜底）

当以上两种策略均不可用时，尝试读取 `cookie.json`（手动保存或旧版 `sso-login.sh` 写入）。

### 手动保存 Cookie

```bash
python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py save-cookie "<cookie_str>" [misId]
```

### 浏览器登录（最终兜底）

1. 设置移动端 viewport：`{"action":"viewport","width":390,"height":844}`
2. 导航到 `https://calendar.sankuai.com`
3. 检查 URL，若跳转到含 `ssosv`、`sso.sankuai.com`、`passport.sankuai.com` 的地址，提示用户：**「登录态已过期，请使用大象/手机扫码登录」**
4. 轮询页面状态（间隔 2-3 秒），检测到业务页面后重新执行 API 调用
5. **登录成功后关闭标签页**：`{"action":"tab_close"}`

## SSO 命令参考

```bash
# 检测当前环境和认证策略
python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py check-env

# 加载 cookie（自动选择策略）
python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py load-cookie

# 一键 CIBA 登录（Sandbox 环境）
python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py ciba-login <misId>

# 手动保存 cookie
python3 ~/.catpaw/skills/room-booking-helper/scripts/rbh_sso.py save-cookie "<cookie_str>" [misId]
```

## 认证失败判断条件

以下任一条件成立时，判定需要重新认证：

- 本地环境：`~/.catpaw/sso_config.json` 不存在或 `ssoid` 字段为空，且 `cookie.json` 也不存在或为空
- Sandbox 环境：`cookie.json` 不存在或为空
- `quick_book.py` 抛出 `AUTH_EXPIRED` 异常
- API 调用返回 `code` 为 `30002`、`401`，或响应体包含 `ssoid` 字段（表示需要重新登录）
- 浏览器访问 `calendar.sankuai.com` 时 URL 包含 `ssosv`、`sso.sankuai.com`、`passport.sankuai.com`

## 认证失败处理流程

当 `quick_book.py` 返回认证失败错误时，按环境选择处理方式：

### 本地环境（catpaw_exchange 策略）

1. 检查 `~/.catpaw/sso_config.json` 是否存在且 `ssoid` 有效
2. 若换票失败，提示用户重新登录 CatPaw Desk 刷新 token
3. 若仍失败，降级到浏览器登录流程

### Sandbox 环境（ciba 策略）

1. 运行 `rbh_sso.py ciba-login <misId>` 发起认证，提示用户在大象中授权
2. 等待授权完成，cookie 自动保存到 `cookie.json`
3. 重试之前失败的操作

## Cookie 注意事项

- ✅ **CatPaw Desk 环境**：`quick_book.py` 自动从 `~/.catpaw/sso_config.json` 换票，无需手动操作
- ✅ **Sandbox 环境**：运行 `rbh_sso.py ciba-login <misId>` 完成认证，cookie 自动保存到 `cookie.json`
- ✅ 不要修改或转义 Cookie 值
- ✅ Cookie 中的特殊字符（如 `**`）是正常编码，无需处理
- ❌ 不要直接使用 `~/.catpaw/sso_config.json` 中的 ssoid 作为 Cookie（需先换票）

## 调用频率限制

为避免对会议室系统造成压力，**请遵守以下频率限制**：

| 操作 | 建议频率 | 说明 |
|------|----------|------|
| 预订请求 | **≤ 1次/10秒** | 提交预订接口（schedules） |
| 查询请求 | **≤ 1次/秒** | 查会议室、查预订等读操作 |
| SSO 登录 | **按需** | Cookie 有效期约 2-4 小时，过期再登录 |

**禁止行为**：
- ❌ 循环轮询会议室状态
- ❌ 批量预订多个会议室囤积
- ❌ 短时间内重复预订-取消操作

**AI 请求标识**：
所有 API 请求都携带 `X-Request-Source: OpenClaw-Agent` header，便于服务端识别和监控。
