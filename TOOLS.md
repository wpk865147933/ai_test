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

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheese sheet.
