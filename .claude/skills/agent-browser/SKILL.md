---
name: agent-browser
description: "无头浏览器自动化 CLI，比内置 browser tool 快 3-10x、省 90% token。基于 Vercel Labs agent-browser v0.18.0 + 4 bug fix + 10 增强（diff 压缩、compact 模式、prompt injection 防护、MCP Server）。实测：热操作 150-300ms，snapshot interactive-only 仅 ~330 token（内置 ~3750）。支持导航、点击、填表、截图(含标注)、DOM 快照、diff、state 持久化。触发词：浏览器、打开网页、截图、网页自动化、填表、爬虫、browse、open page、screenshot、web automation、fill form、scrape、browser、snapshot。"
tags:
  - browser
  - automation
  - web
visibility: private
---

# agent-browser (Patched)

基于 Vercel Labs agent-browser v0.18.0，含 4 bug fix + 10 增强。

> **vs 内置 browser tool**: 速度快 3-10x，token 省 90%（interactive-only ~330 vs ~3750 token）。默认选择 agent-browser，仅在需要 Chrome 接管/hover/drag/PDF/多 Tab 时降级到内置 browser。[对比报告](https://km.sankuai.com/collabpage/2751284351)

## Install

```bash
npm install -g agent-browser && agent-browser install
```

### Apply Patches

```bash
AB_DIR=$(npm root -g)/agent-browser
cd "$AB_DIR"
patch -p1 < <skill_dir>/patches/snapshot-bugfixes.patch
patch -p1 < <skill_dir>/patches/actions-bugfixes.patch
patch -p1 < <skill_dir>/patches/action-policy-default.patch
cp <skill_dir>/patches/command-registry.ts src/
cp <skill_dir>/patches/commands/ src/commands/ -r
cp <skill_dir>/patches/mcp-server.ts src/
```

### Bug Fixes (4)

| # | Module | Bug | Fix |
|---|--------|-----|-----|
| 1 | snapshot.ts | `parseRef("@")` → `""` instead of `null` | Validate eN format after prefix strip |
| 2 | snapshot.ts | Compact mode removes structural parents before checking children | Defer to compactTree() |
| 3 | actions.ts | `"not visible" + "Timeout"` skips not-visible handler | Remove Timeout exclusion |
| 4 | actions.ts | No handler for detached elements | Add detached handler |

### Improvements (10)

| # | Category | Improvement | Impact |
|---|----------|-------------|--------|
| 1 | Token | Diff output compression — only changed lines + 3 context | 70% token reduction in diff |
| 2 | Token | Compact mode as default (`--full` for complete) | 40-50% token reduction |
| 3 | Security | Content boundary markers (random nonce) | Blocks prompt injection |
| 4 | Security | Default restrictive policy (deny eval/download/upload) | Secure by default |
| 5 | Token | Smart truncation (150 lines / 6000 chars) | Prevents context overflow |
| 6 | Security | Download/upload path validation | Blocks path traversal |
| 7 | Security | Socket auth (already in v0.18.0) | Local process isolation |
| 8 | Extensibility | MCP Server adapter (531 lines) | Any MCP client can use browser |
| 9 | Extensibility | Command registry pattern | Plugin-ready architecture |
| 10 | Token | Ref system split: @eN (interactive) / @cN (content) | Cleaner ref numbering |

## Setup (sandbox)

```bash
export AGENT_BROWSER_ARGS="--no-sandbox,--disable-gpu,--disable-dev-shm-usage,--proxy-server=http://nocode-supabase-squid.sankuai.com:443"
```

## Core Workflow

```bash
agent-browser open <url>
agent-browser snapshot -c -i          # Compact + interactive (default)
agent-browser click @e2               # Interactive element
agent-browser fill @e3 "text"
agent-browser get text @c1            # Content element
agent-browser screenshot /tmp/p.png
agent-browser close
```

## Snapshot Strategy

Default is compact mode. Use `--full` for complete tree.

```bash
agent-browser snapshot              # Compact (default since improvement #2)
agent-browser snapshot -i           # Interactive only — smallest
agent-browser snapshot --full       # Complete tree (no truncation)
agent-browser snapshot -s "#main"   # Scoped to selector
agent-browser snapshot --max-lines 200  # Custom truncation limit
```

Auto-truncation at 150 lines / 6000 chars. Disabled with `--full`.

## Ref System

Interactive elements: `@e1`, `@e2` (buttons, links, inputs)
Content elements: `@c1`, `@c2` (headings, paragraphs, cells)

```bash
agent-browser click @e2             # Click button
agent-browser get text @c1          # Get heading text
```

## Diff

```bash
agent-browser snapshot              # Baseline (auto-cached)
agent-browser click @e5             # Action
agent-browser diff snapshot         # Only changed lines + 3 context
```

## Content Boundaries

Snapshot output is wrapped with random nonce to prevent prompt injection:
```
---PAGE-CONTENT-BEGIN-a7f3e2d1---
(page content)
---PAGE-CONTENT-END-a7f3e2d1---
```

Disable with `--no-boundary` for pipe processing.

## Security Defaults

Default policy denies `eval`, `download`, `upload`. Override with `--no-policy`.

## MCP Server

```bash
npx tsx src/mcp-server.ts              # stdio mode
npx tsx src/mcp-server.ts --sse --port 3001  # SSE mode
```

Tools: `browser_open`, `browser_snapshot`, `browser_click`, `browser_fill`, `browser_screenshot`, `browser_get`, `browser_diff`, `browser_close`, `browser_navigate`, `browser_press`, `browser_wait`

## Performance (sandbox, baidu.com)

| Operation | Time |
|---|---|
| Cold open | ~2800ms |
| Snapshot (compact+interactive) | ~260ms |
| Screenshot | ~240ms |
| Click/Fill by ref | ~200-350ms |
| Get title/url | ~155ms |
| Diff snapshot | ~175ms |
| **Average** | **~227ms** |
