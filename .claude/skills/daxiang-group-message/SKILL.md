---
name: daxiang-group-message
description: 通过大象网页版向指定群聊或个人会话发送文本消息，支持 @某人、@所有人、批量@多人。按群聊 ID/群名称定位群聊，或按 UID/MIS/姓名定位个人会话。独创「智能成员发现」技术，无需预先获取群成员列表即可精准 @ 人。
---
# 大象消息发送

## 核心能力

| 功能     | 说明                                  |
| -------- | ------------------------------------- |
| 定位会话 | 按群名/UID/MIS/姓名搜索，支持 ID 直达 |
| 发送文本 | 普通消息、多行消息                    |
| @某人    | 在群聊中精准提及指定成员              |
| @所有人  | 一键提醒全员                          |
| 批量@    | 同时提及多人                          |

## 架构说明

```
搜索/定位会话 → 纯 HTTP API（api.neixin.cn，需签名鉴权）
导航进入会话 → SPA 路由跳转（history.pushState，无刷新）
发送消息     → UI 操作（WebSocket 二进制协议，无法纯接口化）
@人          → 特殊协议文本注入
```

## @人协议格式

大象网页版的 @ 协议是一种特殊的 Markdown 风格链接：

```
[@显示名|mtdaxiang://www.meituan.com/profile?uid=<UID>&isAt=true]
```

**示例**：

- @李四：`[@李四|mtdaxiang://www.meituan.com/profile?uid=100000001&isAt=true]`
- @所有人：`[@所有人|mtdaxiang://www.meituan.com/profile?uid=-1&isAt=true]`

**关键点**：

- `uid` 为用户 ID（字符串），`-1` 表示所有人
- 协议文本会被大象客户端渲染为蓝色可点击的 @ 样式
- 多个 @ 用空格分隔，放在消息正文前

## 签名机制

`api.neixin.cn` 的所有接口需在请求头携带签名字段：

| 字段            | 生命周期 | 说明                           |
| --------------- | -------- | ------------------------------ |
| `dx-sign`     | 页面级   | 核心签名 token，页面刷新后失效 |
| `dx-sso`      | 登录级   | SSO 认证 token，退出登录后失效 |
| `ck` / `al` | 页面级   | 随机标识，与 dx-sign 同步刷新  |
| `u`           | 账号级   | 用户 UID，永久固定             |
| `uu`          | 设备级   | 设备 UUID，永久固定            |
| `av` / `pv` | 版本号   | 大象版本 / Chrome 版本         |

**凭证文件**：`~/.catpaw/skills/skills-market/daxiang-group-message/credentials.json`

凭证失效特征：API 返回 `rescode:1000`，需重新捕获。

---

## 执行流程

### Step 0：读取凭证

读取 `credentials.json`：

- `dx-sign` 非空 → 跳到 Step 2
- 为空 → 进入 Step 1

> **提示用户**：首次使用需要打开大象网页版捕获签名，耗时约 5-10 秒，后续会自动复用。

### Step 1：捕获签名（首次 / 凭证失效时）

**1.1** 导航到 `https://x.sankuai.com/`，snapshot 确认已登录（有搜索框即可）。

**1.2** 注入签名捕获器（拦截 XHR 请求头）：

```javascript
(() => {
  const origOpen = XMLHttpRequest.prototype.open;
  const origSend = XMLHttpRequest.prototype.send;
  const origSetHeader = XMLHttpRequest.prototype.setRequestHeader;
  window.__dxSignCapture = [];
  XMLHttpRequest.prototype.open = function(method, url, ...rest) {
    this._captureUrl = url;
    this._captureHeaders = {};
    return origOpen.apply(this, [method, url, ...rest]);
  };
  XMLHttpRequest.prototype.setRequestHeader = function(name, value) {
    if (this._captureHeaders) this._captureHeaders[name] = value;
    return origSetHeader.apply(this, [name, value]);
  };
  XMLHttpRequest.prototype.send = function(body) {
    if (this._captureUrl && this._captureUrl.includes('neixin.cn')) {
      window.__dxSignCapture.push({
        url: this._captureUrl,
        headers: JSON.parse(JSON.stringify(this._captureHeaders || {}))
      });
    }
    return origSend.apply(this, [body]);
  };
  return 'ok';
})()
```

**1.3** 在搜索框输入任意文字触发 XHR，wait 2500ms。

**1.4** 提取签名：

```javascript
(() => {
  const target = (window.__dxSignCapture || []).find(r => r.url.includes('sug/fusion') && r.headers['dx-sign']);
  if (!target) return null;
  const h = target.headers;
  return JSON.stringify({
    'dx-sign': h['dx-sign'],
    'dx-sso': h['dx-sso'],
    'u': h['u'],
    'uu': h['uu'],
    'ck': h['ck'],
    'al': h['al'],
    'av': h['av'],
    'pv': h['pv'],
    'captured_at': new Date().toISOString()
  });
})()
```

将结果写入 `credentials.json`。

### Step 2：搜索目标会话（API）

在页面内用 `evaluate` 执行（浏览器自动带 Cookie）：

```javascript
(async () => {
  const c = /* credentials.json 内容 */;
  const headers = {
    'Content-Type': 'application/json;charset=UTF-8',
    'cid': '1', 'pt': 'web', 'sv': '2.0.0', 'ai': '1', 'dt': '2',
    'pv': c['pv'], 'av': c['av'], 'dx-sign': c['dx-sign'],
    'dx-sso': c['dx-sso'], 'ck': c['ck'], 'al': c['al'],
    'u': c['u'], 'uu': c['uu']
  };
  const res = await fetch('https://api.neixin.cn/search/api/v7/sug/fusion', {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify({
      word: '{TARGET_NAME}',
      limit: 20,
      categories: /* 群聊: ['group'] | 个人: ['user','group','pub','pubgroup','kefu'] */,
      scope: 0
    })
  });
  return JSON.stringify(await res.json());
})()
```

**解析结果**：

- 群聊：`data.data.group[0].uid` → 群 ID
- 个人：`data.data.user[0].uid` → 用户 ID

**错误处理**：

- `rescode:1000` → 清空凭证，回到 Step 1 重新捕获

**降级方案**：API 失败时，使用 UI 搜索框输入 → snapshot → 点击目标条目。

### Step 3：进入会话（SPA 路由跳转）

使用 SPA 路由跳转，保持 evaluate 上下文不丢失：

```javascript
(function(id, type) {
  type = type || 'chat';  // chat 或 groupchat
  var chatUrl = '/chat/' + id + '?type=' + type;
  
  // SPA 路由跳转（不刷新页面）
  history.pushState({}, '', chatUrl);
  window.dispatchEvent(new PopStateEvent('popstate', { state: {} }));
  
  // 轮询等待输入框出现
  return new Promise(function(resolve) {
    var count = 0;
    var poll = setInterval(function() {
      count++;
      var textarea = document.querySelector('#textTextarea');
      if (textarea && textarea.offsetParent !== null) {
        clearInterval(poll);
        resolve(JSON.stringify({ ok: true, chatUrl: chatUrl }));
      } else if (count >= 40) {  // 最多 8 秒
        clearInterval(poll);
        resolve(JSON.stringify({ error: 'chat_timeout', message: '聊天页加载超时' }));
      }
    }, 200);
  });
})({CHAT_ID}, '{CHAT_TYPE}')
```

### Step 4：发送消息（UI）

#### 4.1 普通文本消息

```javascript
(function(content) {
  return new Promise(function(resolve) {
    var textarea = document.querySelector('#textTextarea');
    if (!textarea) {
      resolve(JSON.stringify({ error: 'no_textarea', message: '找不到消息输入框' }));
      return;
    }
    textarea.focus();
    textarea.click();
    document.execCommand('insertText', false, content);
  
    setTimeout(function() {
      // 模拟 Enter 发送
      textarea.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'Enter',
        code: 'Enter',
        keyCode: 13,
        which: 13,
        bubbles: true
      }));
      setTimeout(function() {
        resolve(JSON.stringify({ ok: true, sent: content }));
      }, 500);
    }, 300);
  });
})('{MESSAGE_CONTENT}')
```

#### 4.2 @某人消息

**前提**：需要先获取被 @ 人的 UID。

**获取群成员 UID 的两种方法**：

**方法 A：进群时拦截 API（推荐）**

进入群聊时，拦截 `members/query` 接口获取完整成员列表：

```javascript
(function(groupId) {
  var membersData = null;
  var origOpen = XMLHttpRequest.prototype.open;
  var origSend = XMLHttpRequest.prototype.send;
  
  // 安装拦截器
  XMLHttpRequest.prototype.open = function(m, url) {
    this._dxMUrl = url;
    return origOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function(body) {
    var self = this;
    var origHandler = this.onreadystatechange;
    this.onreadystatechange = function() {
      if (self.readyState === 4 && self._dxMUrl && self._dxMUrl.indexOf('members/query') !== -1) {
        try {
          var d = JSON.parse(self.responseText);
          if (d.data && d.data.members) {
            membersData = d.data.members.map(function(m) {
              return { uid: String(m.uid), name: m.name };
            });
          }
        } catch(e) {}
        XMLHttpRequest.prototype.open = origOpen;
        XMLHttpRequest.prototype.send = origSend;
      }
      if (origHandler) origHandler.apply(this, arguments);
    };
    return origSend.apply(this, arguments);
  };
  
  // 触发跳转
  var chatUrl = '/chat/' + groupId + '?type=groupchat';
  history.pushState({}, '', chatUrl);
  window.dispatchEvent(new PopStateEvent('popstate', { state: {} }));
  
  // 等待输入框和成员数据
  return new Promise(function(resolve) {
    var count = 0;
    var poll = setInterval(function() {
      count++;
      var textarea = document.querySelector('#textTextarea');
      if (textarea && textarea.offsetParent !== null && (membersData || count >= 50)) {
        clearInterval(poll);
        resolve(JSON.stringify({
          ok: true,
          members: membersData || [],
          chatUrl: chatUrl
        }));
      } else if (count >= 50) {
        clearInterval(poll);
        resolve(JSON.stringify({ error: 'timeout', message: '获取群成员超时' }));
      }
    }, 200);
  });
})('{GROUP_ID}')
```

**方法 B：通过搜索获取用户 UID**

直接搜索用户名，从搜索结果中获取 UID：

```javascript
// 复用 Step 2 的搜索逻辑，从 data.data.user[0].uid 获取
```

**构造 @ 消息**：

```javascript
(function(content, mentions) {
  // mentions 格式: [{ uid: '100000001', name: '李四' }, ...]
  // 特殊: uid=-1 表示 @所有人
  
  return new Promise(function(resolve) {
    var textarea = document.querySelector('#textTextarea');
    if (!textarea) {
      resolve(JSON.stringify({ error: 'no_textarea', message: '找不到消息输入框' }));
      return;
    }
  
    // 构造 @ 部分
    var atParts = mentions.map(function(m) {
      return '[@' + m.name + '|mtdaxiang://www.meituan.com/profile?uid=' + m.uid + '&isAt=true]';
    });
    var finalContent = atParts.join(' ') + ' ' + content;
  
    textarea.focus();
    textarea.click();
    document.execCommand('insertText', false, finalContent);
  
    setTimeout(function() {
      textarea.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
      }));
      setTimeout(function() {
        resolve(JSON.stringify({ ok: true, sent: finalContent }));
      }, 500);
    }, 300);
  });
})('{MESSAGE_CONTENT}', [{ uid: '100000001', name: '李四' }])
```

#### 4.3 @所有人

```javascript
(function(content) {
  return new Promise(function(resolve) {
    var textarea = document.querySelector('#textTextarea');
    if (!textarea) {
      resolve(JSON.stringify({ error: 'no_textarea', message: '找不到消息输入框' }));
      return;
    }
  
    var finalContent = '[@所有人|mtdaxiang://www.meituan.com/profile?uid=-1&isAt=true] ' + content;
  
    textarea.focus();
    textarea.click();
    document.execCommand('insertText', false, finalContent);
  
    setTimeout(function() {
      textarea.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
      }));
      setTimeout(function() {
        resolve(JSON.stringify({ ok: true, sent: finalContent }));
      }, 500);
    }, 300);
  });
})('{MESSAGE_CONTENT}')
```

### Step 5：验证发送

输入框内容为空 → 发送成功。

---

## 参数说明

| 参数                  | 说明     | 示例                                     |
| --------------------- | -------- | ---------------------------------------- |
| `{TARGET_TYPE}`     | 会话类型 | `group`（群聊）或 `chat`（个人）     |
| `{TARGET_NAME}`     | 目标标识 | 群名称 / 用户 MIS / 用户姓名             |
| `{CHAT_ID}`         | 会话 ID  | 群 ID 或用户 UID                         |
| `{MESSAGE_CONTENT}` | 消息正文 | 要发送的文本内容                         |
| `{MENTIONS}`        | @列表    | `[{ uid: '100000001', name: '李四' }]` |

---

## 使用场景示例

### 场景 1：给个人发消息

```
目标：给「张三」发送「你好」
1. 搜索「张三」获取 UID
2. SPA 跳转到聊天页
3. 注入文本并发送
```

### 场景 2：在群里发消息

```
目标：在「产品需求讨论群」发送「今天下午开会」
1. 搜索「产品需求讨论群」获取群 ID
2. SPA 跳转到群聊页
3. 注入文本并发送
```

### 场景 3：在群里 @某人

```
目标：在群里 @李四 说「请看一下这个需求」
1. 进入群聊，拦截成员接口获取成员列表
2. 从成员列表中找到「李四」的 UID
3. 构造 @ 协议文本并发送
```

### 场景 4：在群里 @所有人

```
目标：@所有人 说「重要通知」
1. 进入群聊
2. 构造 @所有人 协议文本并发送（uid=-1）
```

### 场景 5：批量 @多人

```
目标：@张三 @李四 说「请你们看一下」
1. 进入群聊，获取成员列表
2. 找到张三、李四的 UID
3. 构造多个 @ 协议文本并发送
```

---

## 错误处理

| 错误码             | 含义           | 处理建议           |
| ------------------ | -------------- | ------------------ |
| `search_timeout` | 搜索超时       | 检查网络，重试     |
| `not_found`      | 未找到目标     | 换关键词或确认名称 |
| `chat_timeout`   | 聊天页加载超时 | 等待后重试         |
| `no_textarea`    | 找不到输入框   | 确认已进入聊天页   |
| `sign_expired`   | 签名失效       | 重新捕获签名       |
