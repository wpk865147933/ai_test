# 输出格式参考

调整总结风格时只需修改此文件。

## 目录

- [格式选择规则](#格式选择规则)
- [纯文本格式（大象消息）](#纯文本格式大象消息)
- [Markdown 格式（学城/对话）](#markdown-格式学城对话)
- [指定待办人查询](#指定待办人查询)
- [通用规则](#通用规则)

---

## 格式选择规则

根据发送目标自动选择格式：

| 场景 | 格式 | 说明 |
|------|------|------|
| 大象消息输入框（textarea） | 纯文本 | 整群合并为一条消息发送 |
| 学城文档 | Markdown | 保留层级结构 |
| 对话输出 | Markdown | 便于阅读 |

---

## 纯文本格式（大象消息）

适合大象 textarea 发送，整群合并为一条消息。

**文件中转发送流程：**
1. 生成纯文本总结 → 2. 转为 data URL → 3. 通过 fetch 在浏览器中读取并发送

```
+---------------------------------------+
| 与我相关
+---------------------------------------+
[群名A] 待办事项1

+---------------------------------------+
| 群名：{群名}
|
| 日期：{日期范围} · {有效条数} 条消息
|
| >> 群趋势
| * {趋势类型}：{趋势描述}
| * {趋势类型}：{趋势描述}
|
| >> 群待办（有则显示）
| * {待办事项} — @{人}
| * {待办事项} — @{人}
|
| >> 新功能关注（有则显示）
| * {功能名称}：{关注描述}
| * {功能名称}：{关注描述}
|
| 1. {话题标题}
|    {一句话总结，给结论不展开}
|
| 2. {话题标题}
|    ...
|
+---------------------------------------+

+---------------------------------------+
| 群名：{群名2}
|
| ...
|
+---------------------------------------+
```

### 发送辅助函数

```javascript
// 生成 data URL（用于 fetch 发送，完全绕过 JSON 转义问题）
const generateDataUrl = (content) => {
  return 'data:text/plain;base64,' + Buffer.from(content).toString('base64');
};

// 发送单条消息
const sendMessage = async (text) => {
  const dataUrl = generateDataUrl(text);
  
  return await evaluate: `
    (async function() {
      try {
        const response = await fetch('${dataUrl}');
        const content = await response.text();
        
        const ta = document.querySelector('#textTextarea');
        const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
        setter.call(ta, content);
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        
        await new Promise(r => setTimeout(r, 200));
        
        const btn = document.querySelector('div.ctn-send-msg-btn button.send-message-button')
                  || document.querySelector('#textInput .send-message-button')
                  || document.querySelector('button.Auto_SendMsgBtn');
        if (!btn) return { success: false, error: '未找到发送按钮' };
        btn.click();
        
        await new Promise(r => setTimeout(r, 1000));
        
        const remaining = document.querySelector('#textTextarea')?.value?.trim();
        return { success: !remaining, length: content.length };
      } catch (e) {
        return { success: false, error: e.message };
      }
    })()
  `;
};

// 发送多群总结（自动拆分超长内容）
const sendMultiGroupSummary = async (groups) => {
  const results = [];
  
  for (const group of groups) {
    const summary = generateGroupSummary(group); // 按上方格式生成
    
    // 检查长度，超长则拆分
    if (summary.length > 5000) {
      const parts = splitSummary(summary); // 拆分为多部分
      for (let i = 0; i < parts.length; i++) {
        const result = await sendMessage(parts[i]);
        results.push({ group: group.name, part: i + 1, ...result });
        if (!result.success) break;
        await wait(2000);
      }
    } else {
      const result = await sendMessage(summary);
      results.push({ group: group.name, ...result });
      await wait(2000);
    }
  }
  
  return results;
};
```

### 超长内容拆分策略

当单群总结超过 5000 字符时：

```javascript
const splitSummary = (summary) => {
  const parts = [];
  const headerMatch = summary.match(/╔═+╗\n📋 .+?\n\n📅 .+?\n/);
  const header = headerMatch ? headerMatch[0] : '';
  const footer = '╚═+╝';
  
  // 提取所有话题
  const topics = summary.match(/▸ \d+\. .+/g) || [];
  
  // 每批最多 5 个话题
  const batchSize = 5;
  for (let i = 0; i < topics.length; i += batchSize) {
    const batch = topics.slice(i, i + batchSize);
    const partNum = Math.floor(i / batchSize) + 1;
    const totalParts = Math.ceil(topics.length / batchSize);
    
    let part = header.replace(/📋 .+/, (m) => `${m}（${partNum}/${totalParts}）`);
    part += '\n' + batch.join('\n\n');
    if (totalParts > 1) {
      part += '\n\n（更多话题见下一条）';
    }
    part += '\n' + footer;
    
    parts.push(part);
  }
  
  return parts;
};
```

### 发送前自检清单

- [ ] 单条消息不超过 5000 字符（超长已拆分）
- [ ] 使用 data URL 方式发送（绕过 JSON 转义）
- [ ] 每个话题都有 emoji
- [ ] 「与我相关」块已包含（无则显示「无」）
- [ ] 群趋势块已包含（必选）
- [ ] 群待办/新功能关注按需显示（可选）
- [ ] 多群发送时间隔 2 秒以上
- [ ] 发送后验证输入框已清空

### 发送失败处理

```javascript
const sendWithRetry = async (text, maxRetries = 2) => {
  for (let i = 0; i <= maxRetries; i++) {
    const result = await sendMessage(text);
    if (result.success) return result;
    
    console.log(`发送失败，第 ${i + 1} 次重试...`);
    if (i < maxRetries) await wait(3000);
  }
  
  // 最终失败，降级为对话输出
  return { success: false, fallback: text };
};
```

### 发送后验证

```javascript
const verifyAndCleanup = async () => {
  // 验证输入框已清空
  const remaining = await evaluate: `document.querySelector('#textTextarea')?.value?.trim()`;
  if (remaining) {
    console.warn('警告：输入框仍有内容，可能发送失败');
  }
  
  // 可选：清理临时文件（如果使用文件方式）
  // fs.unlinkSync(filePath);
};
```

---

## Markdown 格式（学城/对话）

适合学城文档或对话输出，保留层级结构。

```markdown
> **与我相关**
> - 【{群名}】{事项}

---

## {群名}

**日期：{日期范围}** · {有效条数} 条有效消息

> 筛选：关键词「{xxx}」· 发送人 {xxx}

### 群趋势

- {趋势类型}：{趋势描述}
- {趋势类型}：{趋势描述}

### 群待办（有则显示）

- {待办事项} — @{人}
- {待办事项} — @{人}

### 新功能关注（有则显示）

- {功能名称}：{关注描述}
- {功能名称}：{关注描述}

### 1. {话题标题}

{一句话总结，给结论不展开}

{补充关键细节，2-3句封顶，可省略}

- [{链接标题}]({URL})

---

## 📋 {群名2}
...
```

### 「与我相关」规则

- 从所有群的「群待办」中提取涉及当前用户（按 MIS 或姓名匹配）的条目
- 置于最前面，格式：`【{群名}】{事项}`，不重复 @自己
- 无相关待办时仍保留区块，内容显示「无」：`与我相关\n无`

### 筛选行规则

仅在指定了关键词或发送人时才显示 `> 筛选：` 行，无筛选条件则省略。多个条件用 `·` 分隔。

### 群趋势规则（必选）

**位置：** 紧跟日期行下方，第一个分析区块

**内容：**
- 高频问题：出现 3 次以上的同类问题
- 功能需求：用户明确提出的功能建议
- 重要通知：群合并、版本更新等

**格式：**
- 纯文本：`* {趋势类型}：{趋势描述}`
- Markdown：`- {趋势类型}：{趋势描述}`

---

### 📌 群待办规则（可选）

**位置：** 群趋势下方，新功能关注上方

**内容：**
- 从该群聊消息中提取的待办事项
- 包含事项描述和负责人

**显示规则：**
- 有待办时：正常显示待办列表
- 无待办时：**不显示该区块**

**格式：**
- 纯文本：`* {待办事项} — @{人}`
- Markdown：`- {待办事项} — @{人}`

---

### 新功能关注规则（可选）

**位置：** 群待办下方（或群趋势下方，如果无待办），话题列表上方

**内容：**
- 新发布的功能或工具
- 用户对新功能的讨论和反馈
- 功能上线、版本更新等

**显示规则：**
- 有新功能讨论时：正常显示关注列表
- 无新功能讨论时：**不显示该区块**

**格式：**
- 纯文本：`* {功能名称}：{关注描述}`
- Markdown：`- {功能名称}：{关注描述}`

### 各层级规则

- 群标题：`群名：{群名}`（纯文本格式，不使用 emoji）
- 话题标题：`序号. {话题标题}`（不加句号，不使用 emoji）
- 一句话总结：紧跟标题下方，给结论不展开
- 补充细节：只写标题和总结未覆盖的关键信息，2-3 句封顶，无则省略
- 待办列表：`* {事项} — @{人}`
- 链接：`[{标题}]: {URL}`，只保留有价值的（文档、工具、缺陷），取不到标题则用 URL 本身
- 短回复归入相关话题；转发简写为"(N人转发)"
- 纯文本格式，不使用 Markdown 标记，不使用 emoji，避免 JSON 转义问题

**纯文本格式标记规范（ASCII 字符）：**
| 用途 | 标记 |
|------|------|
| 边框 | `+` `-` `|` |
| 区块标题 | `>>` |
| 列表项 | `*` |
| 序号 | `1.` `2.` ... |
| 与我相关 | `[群名]` |
| 待办负责人 | `@{人}` |

### 多群分隔

多群时每个群的总结块前用 `---` 分隔，单群不加。

---

## 指定待办人查询

当用户指定了「查询待办人」参数时，输出仅包含该人相关的待办汇总，不输出完整话题总结。

```
+---------------------------------------+
| {姓名} 的待办汇总
|
| 日期：{日期范围} · 来源：{N} 个群聊
+---------------------------------------+

[群名A]
* {待办事项1}
* {待办事项2}

[群名B]
* {待办事项3}

共 {M} 条待办
```

### 匹配规则

- 按 MIS 精确匹配或姓名包含匹配（不区分大小写）
- 同一条待办可能有多个 assignees，只要其中一个匹配即命中
- 无匹配结果时输出：`未找到 {姓名/MIS} 的待办事项`

---

## 通用规则

### 字符使用规范（强制）

**纯文本格式使用 ASCII 字符，避免 JSON 转义问题。**

话题标题格式：`序号. {话题标题}`（不加句号，不使用 emoji）

纯文本标记规范：

| 用途 | 标记 | 示例 |
|------|------|------|
| 外边框 | `+` `-` `|` | `+---------------------------------------+` |
| 内分隔 | `|` | `| 群名：CatDesk 内测三群` |
| 区块标题 | `>>` | `>> 群趋势` |
| 列表项 | `*` | `* 高频问题：大模型异常` |
| 序号 | `数字.` | `1. 大模型服务异常` |
| 与我相关 | `[群名]` | `[CatDesk 内测三群] 待办1` |
| 待办负责人 | `@{人}` | `* 修复问题 — @张三` |
| 链接 | `[标题]: URL` | `[技术方案]: https://...` |

**禁止使用的字符（会导致 JSON 转义失败）：**
- 特殊边框符号：`╔` `╗` `╚` `╝` `═` `║` `▸` `•` 等
- Emoji 符号：`🔔` `📋` `📅` `📈` `📌` `🆕` 等
- 其他非 ASCII 特殊符号

**原因：** `browser_action` 的 command 参数是 JSON 字符串，特殊字符会破坏 JSON 结构，导致 `Invalid JSON command` 错误。

### 结构标记规范

**必选标记**（必须出现）：
- `群名：` — 每个群的标题行
- `日期：` — 日期范围行
- `>> 群趋势` — 群趋势块标题（始终保留）
- `与我相关` / `| 与我相关` — 与我相关块标题（始终保留，无待办时显示「无」）
- `[标题]: URL` — 链接行（有链接时）
- `筛选：` — 筛选条件行前缀（有筛选时）

**可选标记**（有内容时显示，无内容时省略）：
- `>> 群待办` — 群待办块标题
- `>> 新功能关注` — 新功能关注块标题

### 发送长度限制

大象单条消息不超过 5000 字符。超长时按群拆分（每群为最小不可拆分单元）。「与我相关」块跟随第一条。

### 写作原则

清楚、简洁、准确。每条要点 1-2 句话，能删则删。给结论不展开。