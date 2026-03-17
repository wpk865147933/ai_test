---
name: daxiang-chat-summary
description: 总结大象群聊聊天记录。通过浏览器自动化抓取大象网页版聊天记录，支持按日期、关键词、发送人筛选。触发词：总结群聊、查询待办。支持交互和定时任务模式，可选发送总结到大象群聊或个人。
---

# 大象群聊总结

浏览器自动化操作 `x.sankuai.com` 聊天记录面板，抓取消息生成总结。

> **兼容性**：依赖 CatPaw Desk 浏览器自动化（sdk-browser-use MCP）、美团内网环境、大象 SSO 登录态。脚本硬编码了 x.sankuai.com 的 DOM 选择器，大象前端改版可能导致选择器失效，届时需更新 `references/selectors.md` 和 `scripts/` 中的对应选择器。

流程：环境准备 → 收集信息 → 整理信息 → 发送信息（可选）

> DOM 选择器集中维护在 `references/selectors.md`，以下步骤中用「选择器名称」引用。
> 面板内元素可能被遮挡，统一用 evaluate 点击。

---

## 第零步：环境准备

### 0.1 收集参数

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| 群名称 | 是 | — | 支持多个 |
| 时间范围 | 否 | 3天 | |
| 关键词 | 否 | — | 按消息内容筛选，多个逗号分隔（取并集） |
| 发送人 | 否 | — | 姓名或 MIS，多个逗号分隔 |
| 输出格式 | 否 | md | Markdown 格式 |
| 查询待办人 | 否 | — | MIS 或姓名，仅输出该人待办 |
| 发送目标 | 否 | 不发送 | 群名或人名 |

交互模式：向用户确认群名（必填）和其他可选参数。
定时任务：从 prompt 取参数，群名缺失则报错退出。

### 0.2 登录检测

```
navigate "https://x.sankuai.com/"
```

等待页面加载完成（使用 poll 轮询搜索框）：
```
evaluate: poll(() => document.querySelector(「搜索框」), 5000)
```
- 返回元素 → 已登录，继续执行
- 返回 null → 检查 URL 是否含 `sso`
  - URL 含 `sso` → 未登录
    - 交互模式：提示扫码，轮询 60s
    - 定时任务：`❌ 登录失败：SSO 过期，请手动登录后重试`
  - URL 不含 `sso` → 页面加载中，等待 3s 后重试一次

---

## 第一步：收集信息

### 1.1 多群批量采集（2个群以上时使用）

读取 `scripts/batch_collect_messages.js`，通过 `window.__BATCH_CONFIG__` 传入参数后 **一次 evaluate** 完成所有群的采集：

```javascript
// 使用 batch_collect_messages.js 脚本
// 1. 设置配置
await evaluate: `window.__BATCH_CONFIG__={groups:["群名1","群名2"],dateStart:"2026年3月12日",dateEnd:"2026年3月13日"};`;
// 2. 执行脚本（读取 scripts/batch_collect_messages.js 内容）
const result = await evaluate: /* batch_collect_messages.js 内容 */;
// 3. 读取完整数据
const fullData = await evaluate: window.__BATCH_RESULTS__.results;
// 4. 清理
await evaluate: delete window.__BATCH_RESULTS__;
```

**内存管理说明**：
- `__BATCH_CONFIG__`：脚本内部自动清理
- `__BATCH_RESULTS__`：需要外部手动清理，避免内存泄漏

脚本内部循环：对每个群在同一页面上下文中依次执行搜索 → 进入 → 打开面板 → 设日期 → 抓取 → 预处理，群间直接通过搜索框切换，无需回首页或刷新页面。

返回值（摘要）：`{ ok, total, success, summary[], note }`
- `summary[]` 中每项：`{ groupName, ok, total, raw, empty, error, notFound, timing }`
- `notFound: true` 表示未找到该群（群名称错误或用户不在群中）
- 详细消息数据存储在 `window.__BATCH_RESULTS__.results` 中
- 读取完整消息：`evaluate: window.__BATCH_RESULTS__.results`
- 清理数据（重要）：`evaluate: delete window.__BATCH_RESULTS__`

**未找到群的处理**：
当 `summary` 中某项有 `notFound: true` 时，应提示用户检查：
1. 群名称是否完全正确（包括特殊符号、空格）
2. 用户是否在该群中

**注意**：
1. 返回数据可能因过大被截断，建议先检查摘要，再按需读取完整消息数据
2. **读取完数据后必须清理**，避免内存泄漏：`evaluate: delete window.__BATCH_RESULTS__`
3. 如需分批读取单个群的消息：`window.__BATCH_RESULTS__.results[i].msgs`

### 1.2 单群采集

单群采集使用同样的 `batch_collect_messages.js` 脚本，只需传入单个群名：
```javascript
await evaluate: `window.__BATCH_CONFIG__={groups:["群名"],dateStart:"...",dateEnd:"..."};`;
const result = await evaluate: /* batch_collect_messages.js 内容 */;
```

---

## 第二步：整理信息

> **⚠️ 必须严格遵循 `references/output-format.md` 中的模板和规则，逐项检查后再输出。**

### 2.1 预处理

脚本已完成：
- 时间排序（从早到晚）
- 过滤（机器人、空消息、去重）
- 待办识别

你需要做的：
- 话题归纳：将相关讨论聚合为话题
- 提取待办：从消息中识别待办事项

### 2.2 待办人筛选（可选）

若指定了「查询待办人」：从所有群的待办中筛选该人条目，仅输出待办汇总。格式详见 `references/output-format.md`「指定待办人查询」。筛选后跳过 2.3，直接到第三步。

### 2.3 按格式生成输出

按 `references/output-format.md` 的「格式选择规则」和对应格式模板生成总结。

### 2.4 输出前自检（必做）

生成总结后、发送/输出前，逐项核对以下清单：

1. **字符安全**：确认输出只包含 ASCII 字符（`+` `-` `|` `*` `>` 等），无 emoji 或特殊符号，避免 JSON 转义问题。
2. **结构标记完整**：`群名：` 标题行、`日期：` 行、`>> 群趋势` 块（必选）、`与我相关` 块、`[标题]: URL` 链接行 — 必须出现；`>> 群待办`、`>> 新功能关注` — 有内容时显示，无内容时省略。
3. **「与我相关」始终保留**：`与我相关` 区块始终输出，无相关待办时内容显示「无」，不省略区块。
4. **区块顺序正确**：紧跟日期行下方的顺序必须是 ① 群趋势（必选）→ ② 群待办（可选，有则显示）→ ③ 新功能关注（可选，有则显示）→ 话题列表。
5. **模板一致性**：对照 `references/output-format.md` 中对应格式的「输出模板」，确认层级结构、分隔符、空行位置与模板一致。
6. **内容质量**：每条话题有一句话总结（给结论不展开），补充细节 2-3 句封顶，无则省略。

---

## 第三步：发送信息（可选）

指定发送目标时执行。

### 3.1 发送方式

**方式一：调用 `daxiang-group-message` 技能（推荐）**

传递参数：
- **目标**：发送目标的群名或人名
- **内容**：总结文本（纯文本格式，ASCII 字符）

**方式二：data URL 中转（直接发送）**

```javascript
const dataUrl = 'data:text/plain;base64,' + Buffer.from(summaryText).toString('base64');

await evaluate: `
  (async function() {
    const text = await (await fetch('${dataUrl}')).text();
    const ta = document.querySelector('#textTextarea');
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(ta, text);
    ta.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise(r => setTimeout(r, 200));
    const btn = document.querySelector('button.send-message-button');
    if (btn) btn.click();
    return { success: true };
  })()
`
await wait: 1000
```

### 3.2 长度控制

- 大象单条消息限制 5000 字符
- 超长时按群拆分（每群为最小不可拆分单元）
- 「与我相关」块跟随第一条消息

---

## 错误处理

- **致命**（中止）：登录失败（定时任务）、群名为空
- **可恢复**（跳过当前群）：群名未找到、面板打开失败、脚本异常、消息为空
- **非致命**（降级）：发送失败 → 对话中输出、发送人匹配不到 → 警告并继续

跳过的群在输出末尾汇总：`[!] 以下群聊处理失败：* {群名} — {原因}`
