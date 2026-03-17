---
name: moa-login-fix
description: 修复 CatClaw 沙箱中 MOA 已安装但无法弹出 SSO 登录验证框的问题。当 MOA 进程正常运行、WSS 16161 端口未监听、重启 MOA 后不弹登录框时使用此 skill。触发词：MOA 不弹登录框、MOA 登录框不出来、MOA WSS 连接失败、moafw 崩溃、ERR_CONNECTION_REFUSED 16161、MOA 登录窗口消失。
---

# MOA 登录框不弹出问题修复

## 问题现象

MOA 已安装且 moatray 进程正在运行，但：
- 重启 MOA 后不弹出 SSO 扫码登录框
- 浏览器访问内网提示「当前设备MOA未安装或未登录」
- WSS 端口 16161 未监听（`ERR_CONNECTION_REFUSED`）
- MOA 日志中无 `SsoWebBrowserWidget` 或 `SsoWindow` 记录

## 根因分析

MOA 的登录弹窗由 `moafw`（防火墙组件）通过 IPC Socket 触发。流程：

```
moafw 启动 → IPC 连接 moatray → 发送登录请求 → moatray 弹出 SsoWebBrowserWidget
```

当 `moafw` 因锁文件冲突或权限问题反复崩溃时，IPC 消息无法送达，moatray 不会弹出登录框。

## 修复流程

### 步骤 1：确认问题

```bash
# 检查 MOA 是否运行
ps aux | grep moatray | grep -v grep

# 检查 WSS 16161 是否监听
ss -tlnp | grep 16161 || echo "16161 NOT listening"

# 检查登录状态
LOG_FILE="/home/.local/share/MOA/logs/moatray-$(date +%Y-%m-%d).txt"
grep -E "ssoLoginStatus|misId" "$LOG_FILE" | tail -5

# 检查 moafw 是否反复崩溃
grep "on_childProcess_finished: /opt/moa/moafw" "$LOG_FILE" | wc -l
```

**确认条件**：moatray 运行中、16161 未监听、moafw 反复崩溃 → 进入步骤 2。

### 步骤 2：启用 QtWebEngine 远程调试

MOA 的登录框是 Qt 内嵌 WebView（非 Chromium 标签页），无法通过 xdotool 操作。需要开启 CDP 端口。

```bash
SUPERVISOR_CONF="/etc/supervisor/supervisord.conf"

# 检查是否已有该配置（9224 避免与 nginx 9223 和 Chromium 9222 冲突）
if grep -q "QTWEBENGINE_REMOTE_DEBUGGING" "$SUPERVISOR_CONF"; then
    echo "已配置"
else
    sed -i '/\[program:moa\]/,/^\[/{
        s|environment=\(.*\)|environment=\1,QTWEBENGINE_REMOTE_DEBUGGING="9224"|
    }' "$SUPERVISOR_CONF"
    echo "已添加 QTWEBENGINE_REMOTE_DEBUGGING=9224"
fi
```

### 步骤 3：重启 MOA 并手动启动 moafw

```bash
# 清理锁文件
rm -f "/home/.local/share/MOA/{B35A0809-43CC-403D-9A28-2D5FE820AADE}" 2>/dev/null
rm -f "/home/.local/share/MOA/{5998AA87-5F99-4B33-8161-A3B2DABEBAB4}" 2>/dev/null

# 重启 MOA
supervisorctl reread && supervisorctl update
supervisorctl restart moa
sleep 10

# 清理 moafw 锁文件并手动启动（关键步骤！）
rm -f "/home/.local/share/MOA/{5998AA87-5F99-4B33-8161-A3B2DABEBAB4}" 2>/dev/null
export DISPLAY=:1
export XDG_RUNTIME_DIR=/tmp/runtime-root
mkdir -p /tmp/runtime-root
/opt/moa/moafw --no-sandbox &
sleep 8
```

**验证登录框是否触发**：

```bash
LOG_FILE="/home/.local/share/MOA/logs/moatray-$(date +%Y-%m-%d).txt"
grep -E "SsoWebBrowser|SsoWindow|IpcServer.*newConnection" "$LOG_FILE" | tail -5
```

出现相关日志 → 登录框已触发，进入步骤 4。

### 步骤 4：通过 CDP 切换到扫码登录

MOA 登录页默认显示 SMS/密码登录，需切换到大象扫码模式。

```bash
# 获取 CDP 页面 ID
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
PAGE_ID=$(curl -s --noproxy '*' http://127.0.0.1:9224/json/list | \
    python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")

# 执行切换脚本
python3 <skill_dir>/scripts/cdp_switch_qr.py "$PAGE_ID"
```

### 步骤 5：截图发送二维码给用户

```bash
sleep 3
# 移走 Chromium 避免遮挡
DISPLAY=:1 xdotool search --name "Chromium" windowminimize 2>/dev/null || true
sleep 1
DISPLAY=:1 scrot /tmp/moa_qr_screen.png
```

将截图发送给用户，提示用大象 App 扫码。

**降级方案**：若截图看不到二维码 → 提示用户到 CatClaw 控制台「浏览器」TAB 手动操作。

### 步骤 6：等待扫码并验证

```bash
for i in $(seq 1 12); do
    LOG_FILE="/home/.local/share/MOA/logs/moatray-$(date +%Y-%m-%d).txt"
    if grep -q '"misId"' "$LOG_FILE" && grep -q '"code":200' "$LOG_FILE"; then
        echo "LOGIN_SUCCESS"
        grep 'misId' "$LOG_FILE" | tail -1 | grep -oP '"misId":"[^"]*"'
        break
    fi
    echo "Waiting... ($((i*15))s)"
    sleep 15
done
```

### 步骤 7：验证内网访问

```bash
supervisorctl restart chromium
sleep 5
```

用 browser 工具访问 `https://km.sankuai.com` 验证不再被拦截。

## 注意事项

- MOA 登录框是 **Qt 内嵌 WebView**，xdotool/xte 无法操作其中的网页元素
- 必须通过 `QTWEBENGINE_REMOTE_DEBUGGING` 开启 CDP 端口后用 JS 操作
- `moafw` 锁文件路径：`/home/.local/share/MOA/{5998AA87-...}`，启动前必须清理
- 二维码约 5 分钟超时，超时后 CDP page ID 会变，需重新获取
- 端口分配：9222=Chromium, 9223=nginx, 9224=MOA QtWebEngine

## 与 moa-login skill 的关系

本 skill 处理 moa-login 流程中「登录框不弹出」的特殊故障。正常流程应先走 moa-login skill，发现登录框无法弹出时再使用本 skill。
