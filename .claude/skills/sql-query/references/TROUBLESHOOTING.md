# Troubleshooting Guide

## uv 安装问题

### macOS / Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装后重启终端，或 `source ~/.bashrc` / `source ~/.zshrc`。

### Windows

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

国内网络超时时，可用 pip 安装：`pip install uv`。

### uv 安装成功但 mtdata 找不到

确认 `~/.local/bin`（macOS/Linux）或 `%USERPROFILE%\.local\bin`（Windows）在 PATH 中：

**macOS / Linux：**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

**Windows（PowerShell）：**
```powershell
[System.Environment]::SetEnvironmentVariable("Path",
    [System.Environment]::GetEnvironmentVariable("Path","User") + ";$env:USERPROFILE\.local\bin",
    "User")
```

修改后重启终端。

---

## 沙箱环境安装持久化（类 OpenClaw）

沙箱容器重启后 `~/.local/` 会被清空，导致 mtdata 丢失。解决方法：将 uv 工具目录指向持久化挂载点。

```bash
export UV_TOOL_DIR="/mnt/openclaw/.uv-tools"
export UV_TOOL_BIN_DIR="/mnt/openclaw/.uv-tools/bin"
uv tool install --upgrade --index-url https://pypi.sankuai.com/simple/ mt-data-cli
```

安装完成后创建软链，确保 `mtdata` 在 PATH 中：

```bash
ln -sf /mnt/openclaw/.uv-tools/bin/mtdata /root/.local/bin/mtdata
```

| 项 | 路径 |
|---|---|
| 工具目录（持久） | `/mnt/openclaw/.uv-tools/mt-data-cli/` |
| 可执行文件（持久） | `/mnt/openclaw/.uv-tools/bin/mtdata` |
| 软链 | `/root/.local/bin/mtdata` → 上面的持久路径 |

重启后 heartbeat 自动恢复软链，无需重新安装。如果软链丢失，重新执行 `ln -sf` 即可。

> `/mnt/openclaw/` 是示例持久化路径，实际路径以沙箱环境配置为准。

### CDP 配置初始化

安装后需运行 `bash <skill_base_dir>/scripts/setup-sandbox.sh`，该脚本自动检测 CDP 端口（`127.0.0.1:9222`）：
- **可达**：写入 `cdp_only: true` + `cdpUrl` 到 `~/.meituan_local_config.json`，mtdata 走 CDP 路径读取 SSO cookie（更可靠）
- **不可达**：自动跳过，保持默认（`browser_cookie3` 直接读 Chromium 文件也能工作）

> 注意：`cdp_only: true` 设置后，如果 Chromium 未运行导致 CDP 不可达，mtdata 会报错而不会回退。此时删除配置中的 `cdp_only` 字段即可恢复。

---

## Authentication Errors (401 / SSO 认证失败)

**Symptom**: `mtdata` 命令失败，提示鉴权错误或无法获取 cookie。

### 标准开发机（有浏览器）

1. 用 Chrome 打开美团内网并登录（`corp.sankuai.com`）
2. 测试：`mtdata table search 订单 --limit 1`
3. 如仍失败，检查配置：`cat ~/.meituan_local_config.json | grep -A5 sso`

### 沙箱环境（类 OpenClaw）

认证链路：mtdata → CDP 连接沙箱 Chromium (127.0.0.1:9222) → 读取 TGCN cookie → MOA 登录后自动写入。

**确认配置**：`~/.meituan_local_config.json` 需包含：
```json
{ "sso": { "cdp_only": true }, "browser": { "cdpUrl": "http://127.0.0.1:9222" } }
```

**排查步骤**：
1. 确认 MOA 已登录（手机端处于登录状态）
2. 确认沙箱 Chromium 正在运行：`curl -s http://127.0.0.1:9222/json/version | head -1`
3. 如认证失败，触发 moa-login skill 重新走安装+扫码流程

### 桌面 AI 工具（类 CatPaw Desk）

CatPaw Desk 在 `~/.catpaw/sso_config.json`（Windows 为 `%APPDATA%\CatPaw\sso_config.json`）中维护有效的 ssoid。注入脚本将其写入 mtdata 的本地加密缓存，全程无系统密码弹窗：

**macOS / Linux：**
```bash
python3 <skill_base_dir>/scripts/sso-inject.py            # 注入 SSO
python3 <skill_base_dir>/scripts/sso-inject.py --check    # 仅查看缓存状态
```

**Windows PowerShell：**
```powershell
python <skill_base_dir>\scripts\sso-inject.py            # 注入 SSO
python <skill_base_dir>\scripts\sso-inject.py --check    # 仅查看缓存状态
```

SSO 过期后重新运行即可。前提：CatPaw Desk 已登录美团内网。

**备用方案**：如果脚本注入失败，mtdata 会自动尝试从系统浏览器的 Cookie 存储中读取 bi_ssoid。确保 Chrome/Edge/Arc 浏览器已登录 bi.sankuai.com。

---

## 网络连接问题

### VPN 连接检查

**Symptom**: 连接 bi.sankuai.com 失败，提示网络超时或连接被拒绝。

**排查步骤**：
1. 确认已连接公司 VPN（如 AnyConnect、深信服等）
2. 测试基础连接：`ping bi.sankuai.com`
3. 如果 ping 不通，请检查 VPN 连接状态或联系网络管理员
4. **境外用户**：如果在境外网络环境，需要使用境外域名 `bi.keetapp.com`，所有命令通过 `--base-url https://bi.keetapp.com` 参数传入

### 502 Bad Gateway

**Symptom**: 部分命令（如 `table search`、`table schemas`）偶尔返回 502。

上游服务临时抖动，稍等片刻重试即可。如持续出现请联系数据平台团队。
