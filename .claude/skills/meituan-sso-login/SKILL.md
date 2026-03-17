---
name: meituan-sso-login
description: 美团内网 SSO 统一登录 Skill。提供分段式 SSO 登录流程（不阻塞 Agent）和 Cookie 提取能力。其他需要访问 sankuai.com 内网的 Skill 可依赖此 Skill 完成认证。当浏览器访问 sankuai.com 被 SSO 拦截、API 请求返回 401/302/AUTH_REQUIRED、或其他 Skill 需要获取内网 Cookie 时触发。
---

# 美团内网 SSO 统一登录

## 核心能力

1. **SSO 登录**（分段式，不阻塞 Agent）
2. **Cookie 提取**（CDP 实时从浏览器获取）

## 登录流程（分段式）

**原则：每一步都是秒级返回，Agent 不被阻塞，用户能实时收到消息。**

### Step 1: 启动登录

确保浏览器在 SSO 登录页后：

```bash
python3 <skill_dir>/scripts/sso_login.py start --output /tmp/sso_qrcode.png
```

输出：
- `QRCODE_SAVED:/tmp/sso_qrcode.png` — 二维码已保存
- `CTX_ID:xxx` — 会话 ID

Agent 拿到二维码后上传 S3Plus，**必须使用 `message tool`（action=send）主动推送大象消息，不能等 turn 结束再回复**（否则用户在大象收不到实时消息）：

```
🔐 需要登录内网系统

请用大象扫描下方二维码完成登录：

⚠️ **扫码并确认后，我会自动完成后续操作，不需要回复我**

![SSO登录二维码]({s3plus_url})
```

> ⚠️ **发完消息后立即开始轮询，不要等用户回复，立刻执行 Step 2。**

### Step 2: 轮询状态（发完二维码后立即开始，每次单独调用）

> ⚠️ **每次单独调用一次，根据输出决定下一步，不要用 shell for/while 循环包裹。每次调用间隔 3-5 秒（用 `sleep 4` 隔开），最多重试 20 次。**

```bash
sleep 4
python3 <skill_dir>/scripts/sso_login.py status
```

| 输出 | 含义 | Agent 下一步 |
|------|------|-------------|
| `SCANNING` | 等待扫码 | sleep 4，再调一次 status |
| `SCAN_SUCCESS` | 已扫码待确认 | sleep 4，再调一次 status |
| `CONFIRMED` | 已确认 | sleep 2，再调一次 status（等前端跳转） |
| `SKIP_READY` | 页面出现 Skip 按钮 | 立即执行 Step 3（点 Skip） |
| `REDIRECTED` | 已跳转到目标页 | 立即执行 Step 4（verify） |
| `EXPIRED` | 二维码过期 | 通知用户重新扫码，重新 start |
| `NO_SESSION` | 没有登录会话 | 先调 start |

### Step 3: 点击 Skip

**分两步：先检测，再用 browser tool 点击**

3a. 检测 Skip 按钮：

```bash
python3 <skill_dir>/scripts/sso_login.py skip
```

输出：
- `SKIP_FOUND:Skip` + `USE_BROWSER_TOOL_TO_CLICK` — 检测到按钮
- `SKIP_FAILED:xxx` — 未找到按钮

3b. 用 browser tool 点击（因为 SSO 页面是 React 组件，CDP JS 无法触发点击）：

```
browser snapshot profile="openclaw" → 找到 Skip 按钮的 ref
browser act profile="openclaw" request={"kind":"click","ref":"<skip_ref>"}
```

通常 Skip 按钮的 ref 为 `e5`（在 Passkey 页面中）。

### Step 4: 验证

```bash
python3 <skill_dir>/scripts/sso_login.py verify
```

输出：
- `LOGIN_SUCCESS:https://dev.sankuai.com/...` — 登录成功
- `NOT_YET:https://ssosv...` — 还没完成

## Cookie 提取

登录成功后，其他 Skill 通过此脚本获取 Cookie：

```bash
# Cookie 字符串
python3 <skill_dir>/scripts/extract_cookies.py --domain dev.sankuai.com

# JSON 格式 + 验证有效性
python3 <skill_dir>/scripts/extract_cookies.py \
  --domain dev.sankuai.com \
  --format json \
  --check-url "https://dev.sankuai.com/rest/api/2.0/users"
```

## 完整 Agent 调用流程示例

```
1. browser navigate → SSO 页面
2. sso_login.py start → 拿到二维码
3. 上传 S3Plus → 发大象消息给用户
4. sleep 4 → 单次调用 sso_login.py status → 根据输出决定下一步
   ↳ SCANNING/SCAN_SUCCESS → sleep 4 → 再调一次 status
   ↳ CONFIRMED → sleep 2 → 再调一次 status
   ↳ SKIP_READY → 执行第5步
   ↳ REDIRECTED → 执行第6步
   ↳ EXPIRED → 通知用户，重新 start
5. sso_login.py skip → browser tool 点击 Skip 按钮 → 回到第4步继续轮询
6. sso_login.py verify → LOGIN_SUCCESS → 继续原操作
```

> ⚠️ **第4步每次都是单独的 exec 调用（sleep + status），绝对不要用 shell for/while 循环包裹所有轮询。**

## 注意事项

- Cookie 不缓存到文件，每次通过 CDP 实时提取
- 二维码有效期约 5 分钟，过期需重新 start
- SSO Cookie 有效期约 8 小时
- start 会刷新 SSO 页面（获取新二维码），刷新后 SSO 前端 JS 会自动轮询状态并在扫码后跳转到 access-control 页面
- skip 直接在当前页面 DOM 中查找 Skip 按钮，不依赖 URL 变化

## 文件结构

```
meituan-sso-login/
├── SKILL.md
├── data/
│   └── sso_state.json        # 登录状态（自动管理）
└── scripts/
    ├── sso_login.py           # 分段式登录（start/status/skip/verify）
    ├── extract_cookies.py     # Cookie 提取
    └── capture_sso_qrcode.py  # 旧版二维码捕获（兼容）
```
