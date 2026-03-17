---
name: meituan-sso
description: |
  美团内网 SSO 统一认证 Skill。处理 CatClaw/OpenClaw 沙箱中访问 sankuai.com 内网时的 MOA 安装、SSO 登录全流程。
  触发场景：(1) 访问 .sankuai.com 被 MOA 或 SSO 拦截 (2) browser 返回 401/SSO 页面 (3) 其他 skill 内网访问前置认证
  关键词：MOA 登录、SSO 扫码、内网认证、401、sankuai.com 拦截
---

# 美团内网 SSO 认证

## 适用环境

- CatClaw 沙箱（主要）
- OpenClaw 沙箱（需有 Chromium + supervisor）
- 不适用于：本地开发机、Cowork、纯 CLI 环境（无浏览器）

## 核心规则

1. **沙箱内访问内网必须用 `browser` 工具**，`web_fetch`/`curl` 走不了 MOA 代理
2. **必须指定 `profile="openclaw"`**（沙箱内置 Chromium，CDP 端口 9222）
3. **Cookie 自动持久化** — browser 的 Chromium profile 自动保存，不需要手动导出/导入
4. **不要用 `browser getCookies`** — 该 API 不存在
5. **不要用 `/api/user/info` 检测登录态** — 可能 404，直接导航目标页 + snapshot 判断

---

## 总流程

```
检测 MOA → 检测 SSO 登录态 → [需要登录] → SSO 扫码 → 验证 → 访问目标 URL
```

---

## Phase 1：MOA 环境检测与修复

### 1.1 检查 MOA 安装和运行状态

```bash
# 一次性检测
MOA_INSTALLED=$(dpkg -l moa 2>/dev/null | grep -c "^ii")
MOA_RUNNING=$(ps aux | grep moatray | grep -v grep | wc -l)
echo "installed=$MOA_INSTALLED running=$MOA_RUNNING"
```

| installed | running | 操作 |
|-----------|---------|------|
| 0 | - | → 1.2 安装 MOA |
| 1 | 0 | → 1.3 启动 MOA |
| 1 | 1 | → 1.4 检查 MOA 登录 |

### 1.2 安装 MOA

```bash
bash <skill_dir>/scripts/install_moa.sh
```

脚本自动完成：配置 hosts → chromium 代理 → 下载安装 MOA → supervisor 守护进程。
安装后等待 10 秒再继续。

### 1.3 启动 MOA

```bash
supervisorctl start moa
sleep 5
```

### 1.4 检查 MOA 登录状态

```bash
LOG_FILE="/home/.local/share/MOA/logs/moatray-$(date +%Y-%m-%d).txt"
grep -E "ssoLoginStatus is 0|misId" "$LOG_FILE" 2>/dev/null | tail -3
```

- 有 `misId` → MOA 已登录，进入 Phase 2
- 无匹配 → 需要 MOA 扫码登录，执行 1.5

### 1.5 MOA 扫码登录

```bash
supervisorctl restart moa
sleep 8  # 等待登录弹框加载
```

然后通过浏览器自动化处理 MOA 登录弹框：
1. MOA 重启后会在 Chromium 中弹出登录框
2. 登录框有 SMS/Password/Email Code 三种方式
3. 点击登录框右上角的**二维码图标**切换到扫码模式
4. 截图发送给用户 → 用户用大象 App 扫码
5. 扫码后可能出现授权确认框 → 点击同意 → 关闭弹框
6. 等待最多 3 分钟，每 15 秒检查日志变化

---

## Phase 2：SSO 登录态检测

### 2.1 用 browser 验证登录态

```
browser navigate targetUrl="https://km.sankuai.com" profile="openclaw"
```

等待页面加载后：

```
browser snapshot profile="openclaw" compact=true
```

**判断逻辑：**
- snapshot 中有学城导航栏（搜索、主页、我的空间等）→ ✅ 登录态有效，跳到 Phase 4
- URL 跳转到 `ssosv.sankuai.com` → ❌ SSO 过期，进入 Phase 3
- 页面空白/超时/MOA 拦截 → 回 Phase 1 检查 MOA

---

## Phase 3：SSO 扫码登录

### 方案 A：自动捕获二维码（推荐）

通过 CDP 拦截 SSO 页面的二维码生成请求，提取原始图片：

```bash
python3 <skill_dir>/scripts/capture_sso_qrcode.py \
  --output /tmp/sso_qrcode.png \
  --timeout 60 \
  --cdp-port 9222
```

脚本工作流程：
1. 通过 CDP WebSocket 连接到 SSO 页面
2. 启用 Network 域监听
3. `Page.reload` 刷新页面触发新的二维码请求
4. 拦截 `ssosv.sankuai.com/sson/auth/qrcode/v1/generate` 的响应
5. 从响应体提取二维码图片（支持 base64/JSON 嵌套/URL 等格式）
6. 保存到 `--output` 指定路径

**捕获成功后：**
1. 上传到 S3Plus 获取可访问 URL：
   ```bash
   SANDBOX_ID=$(hostname)
   python3 <skill_dir>/scripts/upload_s3plus.py \
     --file /tmp/sso_qrcode.png \
     --env prod-corp \
     --object-name ${SANDBOX_ID}/sso_qrcode.png
   ```
2. 发送大象图片消息给用户：
   ```
   系统需要 SSO 登录，请用大象 App 扫码，二维码 5 分钟内有效：

   ![SSO登录二维码](<s3plus_url>)
   ```
3. 等待用户回复"已扫码"/"登录了"等确认

### 方案 B：引导用户手动扫码（降级）

当方案 A 失败时（CDP 连接异常、脚本报错等）：

```
SSO 自动登录失败，请手动操作：
1. 打开 CatClaw 控制台：https://nocode.sankuai.com/#/cat-claw
2. 点击顶部「浏览器」标签页
3. 点击「浏览器扫码登录」按钮
4. 用大象 App 扫描二维码
5. 扫码成功后必须点击「跳过」（否则 Cookie 不生效）
6. 完成后告诉我
```

### 3.1 验证登录

用户确认后：

```
browser navigate targetUrl="https://km.sankuai.com" profile="openclaw"
browser snapshot profile="openclaw" compact=true
```

- 正常加载 → ✅ 登录成功，进入 Phase 4
- 仍在 SSO 页 → 提醒用户重试，确认点了「跳过」
- 二维码过期 → 重新执行方案 A（脚本会刷新页面生成新二维码）

---

## Phase 4：访问目标 URL

```
browser navigate targetUrl="<用户原始请求的 URL>" profile="openclaw"
browser snapshot profile="openclaw"
```

正常处理页面内容，继续执行原始任务。

---

## 集成接口

其他 skill 需要内网访问时，按以下模式集成：

```
1. browser navigate targetUrl="<内网 URL>" profile="openclaw"
2. browser snapshot → 检查是否被拦截
3. 如果 URL 含 ssosv.sankuai.com → 触发本 skill 的 Phase 3
4. 如果页面空白/MOA 拦截 → 触发本 skill 的 Phase 1
5. 正常页面 → 继续原 skill 逻辑
```

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `web_fetch`/`curl` 访问内网 401 | 不走 MOA 代理 | 改用 `browser navigate profile="openclaw"` |
| browser 报 "no tab connected" | 用了默认 chrome profile | 指定 `profile="openclaw"` |
| 扫码后仍被 SSO 拦截 | CatClaw 控制台没点「跳过」 | 重新扫码，必须点「跳过」 |
| MOA 安装失败 | 网络问题/权限不够 | 检查网络，确认 root 权限 |
| `agent-browser` 访问内网 401 | 独立 Chromium，无 MOA 登录态 | 不支持，必须用 `browser` 工具 |
| 二维码过期 | 超过 5 分钟 | 重跑 capture_sso_qrcode.py（自动刷新） |
| CDP 连接失败 | Chromium 未启动或端口不对 | `supervisorctl restart chromium`，确认 9222 端口 |

## 反模式（不要做）

- ❌ `browser getCookies` — API 不存在
- ❌ 手动导出/导入 Cookie 到 JSON 文件 — browser profile 自动持久化
- ❌ 省略 `profile="openclaw"` — 默认走 chrome 扩展，不是沙箱浏览器
- ❌ 检测登录态用 `/api/user/info` — 可能 404
- ❌ 每次登录后写 TOOLS.md — 不需要

## 文件结构

```
meituan-sso/
├── SKILL.md                          # 本文件
└── scripts/
    ├── install_moa.sh                # MOA 安装脚本（Phase 1.2）
    ├── capture_sso_qrcode.py         # SSO 二维码 CDP 捕获（Phase 3A）
    └── upload_s3plus.py              # S3Plus 上传（Phase 3A）
```
