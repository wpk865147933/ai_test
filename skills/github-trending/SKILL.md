---
name: github-trending
description: 获取 GitHub Trending 热门项目，支持按时间范围筛选（daily/weekly/monthly）。使用公开页面抓取，无需 API Key。
---

# GitHub Trending

自动获取 GitHub Trending 热门项目信息。

## 使用方法

```bash
# 获取今日热门
github-trending

# 获取本周热门
github-trending weekly

# 获取本月热门
github-trending monthly

# JSON 格式输出
github-trending json
```

## 数据源

- URL: https://github.com/trending
- 无需认证
- 实时获取
