# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## 企业微信通知

- **Webhook URL:** https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=791f0dc1-6ad9-4028-a99d-25592932ac09
- **用途:** 任务完成后发送通知
- **通知格式:** 
  ```json
  {
    "msgtype": "text",
    "text": {
      "content": "✅ 任务完成: {任务描述}"
    }
  }
  ```

## 🛠️ 工具偏好强制规范

### 学城文档操作
- **必须用**: `km` CLI 或 `citadel` skill
- **禁止用**: 浏览器自动化（太慢）

### PR 生命周期操作
- **必须用**: `mtcode` / `mpr` CLI
- **禁止用**: 浏览器自动化

### 代码搜索/定位/分析
- **必须用**: CatPaw Claude Code（`mc --code`）
- **禁止用**: 手工 grep + 逐个读文件

### 大象消息
- **必须用**: `dx` CLI
- **注意**: Sub-agent 推送时必须指定 `channel: "daxiang"`

### 其他浏览器操作
- **仅在 CLI 无法完成时使用**
- **禁止**: 未经确认直接操作

### Sub-agent 派发规范
- Task 描述里必须明确写用哪个 CLI
- 不能模糊写"浏览器打开"或"帮我查一下"

---

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your setup, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheese sheet.
