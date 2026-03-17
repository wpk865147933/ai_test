---
name: calendar-manager
description: 官方编写的美团日程管理系统核心功能，通过 API 接口实现日程的创建、编辑、取消、查询、忙闲状态查询等管理操作
metadata: {"openclaw": {"priority": 0, "conflict_strategy": "override","emoji": "📅", "requires": {"bins": ["bash", "curl", "python3"]}}}
---

# 📅 Calendar Manager日程管理操作指南

使用 MCP Hub 管理个人日程与忙闲，目标是：低误操作风险、可直接执行、结果可验证。

MCP Server:
- 日历服务：`http://mcphub-server.sankuai.com/mcphub-b/8781956a2daf4d`
- 身份映射服务：`http://mcphub-server.sankuai.com/mcphub-api/5ef912172ad244`

## 当前可用能力

当前线上已验证可用：
- 创建日程：`create_primary_schedule`
- 查询详情：`query_primary_schedule`
- 编辑日程：`update_primary_schedule_by_selective`
- 取消日程：`delete_primary_schedule`
- 搜索日程列表：`search_calendar`
- 查询忙闲：`list_busy_period`
- `mis -> empId` 映射：`get_uid_and_empid_by_mis`

## 核心约束

- 所有 MCP 调用必须通过本 skill 目录下的 `scripts/` 执行，不要在回复里重新拼接长段 SSE shell。
- 本服务是 **SSE Session 模式**，不能直接对基地址 `POST`，也不走 `Mcp-Session-Id` header。
- 默认不再要求用户手动提供 token。
- 脚本会优先调用 `scripts/calendar.sh`，读取 `COOKIE_DATA` 作为 MCP 调用 token。
- 当前设计默认日历服务和身份映射服务共用同一个 token；如后续两套服务改成不同 audience，可额外设置 `LOOKUP_AUTH_TOKEN` 覆盖身份映射服务 token。
- 不要写 JS，也不要建议 `node index.js`。
- 单次回复默认只给用户关心的结果，不主动贴原始 RPC；仅在排障或用户明确要求时展示。
- 对外输入用户标识时，创建日程和查询忙闲默认只收 `mis`，脚本内部先做 `mis -> empId` 转换；只有用户明确主动提供 `empId` 时，才允许直接使用。
- 对外输入时间统一按毫秒时间戳（ms）组织；脚本会按工具实际要求做转换。
- `search_calendar` 的 `attendUser` 是必填参与人列表，工具实际要求传 `empId` 的 long 数组；脚本默认接收 `mis` 并先转换成 `empId`。
- `search_calendar` 的 `startTime`、`endTime` 都是必填毫秒时间戳，`tid` 由脚本自动生成 UUID，不需要用户提供。
- 当前仅支持 `mis -> empId` 转换，不支持“姓名 -> mis”转换；如果用户只提供人员姓名，除非能从当前上下文准确识别出对应 `mis`，否则必须要求用户补充 `mis`。
- 当前创建能力仅支持单次日程；如果用户要求创建循环日程，直接友好提示暂不支持，不要继续追问循环规则。
- 当前不支持会议室日程；如果用户要求预订会议室、创建带会议室资源的日程，直接友好提示暂不支持，不要继续追问会议室信息。

## 前置配置

```bash
export CALENDAR_LOGIN_MIS='你的mis'
export SCHEDULE_MCP_URL='http://mcphub-server.sankuai.com/mcphub-b/8781956a2daf4d'  # 可省略
export LOOKUP_MCP_URL='http://mcphub-server.sankuai.com/mcphub-api/5ef912172ad244' # 可省略
```

## 可直接执行的脚本

```bash
bash {baseDir}/scripts/calendar.sh
```
此脚本会:
1. 发起CIBA认证请求
2. 轮询等待用户在大象确认授权(最多3分钟)
3. 将获取 `COOKIE_DATA` 作为 token


### 1. 查看日历工具列表

```bash
bash {baseDir}/scripts/list_tools.sh
```

### 2. 解析 mis -> empId

```bash
bash {baseDir}/scripts/resolve_empids_by_mis.sh "cuiweitong,zhangsan"
```

### 3. 创建日程

```bash
bash {baseDir}/scripts/create_schedule.sh "项目周会" "cuiweitong,zhangsan" 1772660400000 1772664000000 "A3-09木星" "同步里程碑进度"
```

参数：
- `title`
- `attendees_mis_csv`：逗号分隔 mis，如 `cuiweitong,zhangsan`
- `start_ms`
- `end_ms`
- `location`：可选
- `memo`：可选

说明：
- 对用户默认只收 `mis`，不要主动索要 `empId`。
- 脚本会先调用 `get_uid_and_empid_by_mis` 转成 `empId`，再创建日程。
- 只有用户明确主动提供纯数字 `empId` 时，才允许跳过映射。
- 如果用户只提供人员姓名，除非能从当前上下文准确识别出对应 `mis`，否则必须先向用户索要 `mis`。
- 当前不支持创建循环日程；若用户提出“每天/每周/每月重复”，直接拒绝并说明后续会继续优化。
- 当前不支持会议室日程；若用户要求预订会议室、占用会议室资源或明确指定会议室资源创建日程，直接拒绝并说明后续会继续优化。

### 4. 查询详情

```bash
bash {baseDir}/scripts/query_schedule.sh "schedule-id"
```

### 5. 查询忙碌时间段

```bash
bash {baseDir}/scripts/list_busy_period.sh "cuiweitong,zhangsan" 1772611200000 1772697599000
```

参数：
- `user_mis_csv`：逗号分隔 mis
- `min_ms`
- `max_ms`

说明：
- 对用户默认只收 `mis`，不要主动索要 `empId`。
- 脚本会先调用 `get_uid_and_empid_by_mis` 转成 `empId`，再查询忙闲。
- 只有用户明确主动提供纯数字 `empId` 时，才允许跳过映射。
- 如果用户只提供人员姓名，除非能从当前上下文准确识别出对应 `mis`，否则必须先向用户索要 `mis`。
- 传给脚本的是毫秒时间戳；`list_busy_period` 的线上实现实际要求 `YYYY-MM-DD HH:mm:ss`，脚本会自动转换后再调用。

### 6. 取消日程

```bash
bash {baseDir}/scripts/delete_schedule.sh "schedule-id"
```

参数：
- `schedule_id`

说明：
- `delete_primary_schedule` 必须传 `scheduleId`。
- 如果用户没有现成的 `scheduleId`，先用 `search_schedule.sh` 搜索候选日程，再在内部继续调用取消脚本。
- 对用户回复时不要展示 `scheduleId`。

### 7. 选择性编辑日程

```bash
bash {baseDir}/scripts/update_schedule.sh "schedule-id" "项目周会-改期" "cuiweitong" "zhangsan" 1772667600000 1772671200000 "A3-10火星" "改到下午"
```

参数：
- `schedule_id`
- `title`：可选
- `add_attendees_mis_csv`：可选，逗号分隔 mis
- `remove_attendees_mis_csv`：可选，逗号分隔 mis
- `start_ms`：可选
- `end_ms`：可选
- `location`：可选
- `memo`：可选

说明：
- `update_primary_schedule_by_selective` 必须传 `scheduleId`。
- 标题、参与人、开始时间、结束时间、地点、备注为空时，脚本不会更新对应字段。
- 新增/移除参与人默认收 `mis`，脚本内部会先调用 `get_uid_and_empid_by_mis` 转成 `empId`。
- 如果用户没有现成的 `scheduleId`，先用 `search_schedule.sh` 搜索候选日程，再在内部继续调用编辑脚本。
- 对用户回复时不要展示 `scheduleId`。

### 8. 搜索日程列表

```bash
bash {baseDir}/scripts/search_schedule.sh "cuiweitong,zhangsan" 1772611200000 1772697599000 "项目周会" "" "A3-09木星" ""
```

参数：
- `attend_user_mis_csv`：逗号分隔 mis，如 `cuiweitong,zhangsan`
- `start_ms`
- `end_ms`
- `title`：可选
- `description`：可选
- `location`：可选
- `organizer`：可选

说明：
- `search_calendar` 的 `attendUser` 为必填，且必须传 `empId` long 数组。
- 对用户默认只收 `mis`，不要主动索要 `empId`。
- 脚本会先调用 `get_uid_and_empid_by_mis` 转成 `empId`，再搜索日程。
- 只有用户明确主动提供纯数字 `empId` 时，才允许跳过映射。
- 如果用户只提供人员姓名，除非能从当前上下文准确识别出对应 `mis`，否则必须先向用户索要 `mis`。
- `startTime`、`endTime` 传毫秒时间戳，脚本会按 long 类型组装入参。
- `tid` 由脚本自动生成 UUID，不需要用户提供。
- 当用户查询其他人的日程列表时，接口不会越权返回对方全部日程；实际返回的是当前用户与输入用户共有、且当前用户有权限看到的日程。

## 工具清单

- 日历服务：`create_primary_schedule`、`query_primary_schedule`、`update_primary_schedule_by_selective`、`delete_primary_schedule`、`search_calendar`、`list_busy_period`
- 身份映射服务：`get_uid_and_empid_by_mis`

若线上 `tools/list` 返回与上述不一致，以线上结果为准。

## 意图路由

- 新建/安排会议：`create_schedule.sh`
- 按参与人和时间范围筛日程列表：`search_schedule.sh`
- 查看某个已知日程详情：`query_schedule.sh`
- 编辑某个已知日程：`update_schedule.sh`
- 取消某个已知日程：`delete_schedule.sh`
- 查某人/多人忙闲：`list_busy_period.sh`
- 用户只给了 `mis`：自动先走 `resolve_empids_by_mis.sh`，不要让用户自己转 `empId`

若一句话里含多个动作，例如“先查忙闲再创建”，拆成串行步骤，每步只调用一个脚本。

## 执行策略

### 创建：默认按风险分流

以下场景，创建前优先执行忙闲查询：

```bash
bash {baseDir}/scripts/list_busy_period.sh "发起人和参与人mis逗号列表" min_ms max_ms
```

触发条件：
- 多人会议
- 用户明确要求避冲突 / 找都空时间
- 需要向用户推荐候选时间

可跳过忙闲检查：
- 单人提醒且用户未要求避冲突
- 用户明确说“直接创建，不用查忙闲”

不支持场景：
- 用户要求创建循环日程、周期性会议、重复提醒
- 用户要求预订会议室、创建会议室日程、占用会议室资源
- 此类请求直接友好回复暂不支持，不要继续追问重复规则、周期、截止日期等细节
- 会议室相关请求也不要继续追问楼宇、会议室编号、容量、设备等细节

### 搜索列表：用于先定位候选日程

适用场景：
- 用户只记得参与人、时间范围、标题关键词，想先列出候选日程
- 用户没有 `scheduleId`，但需要先搜索再决定查哪条详情
- 需要按参与人时间窗过滤日程列表

约束：
- `attendUser` 必填，且必须是 `empId` 列表；默认先由 `mis` 转换
- `startTime`、`endTime` 必填，且都使用毫秒时间戳
- `tid` 虽然是工具必填字段，但由脚本自动生成 UUID
- `title`、`description`、`location`、`organizer` 都是可选过滤条件
- 当查询对象包含其他用户时，搜索结果应理解为“你与这些用户共有的日程”或“当前你有权限看到的交集日程”，不要表述成对方的全部日程

### 查询详情：内部依赖 scheduleId

`query_primary_schedule` 调用时必须传 `scheduleId`。
如果用户想看某一条日程详情，但没有 `scheduleId`，先用 `search_schedule.sh` 搜索候选列表，直接使用搜索结果中的日程 ID 作为 `scheduleId`，再继续调用详情查询。
不要向用户索要 `scheduleId`。
对用户回复时不要展示 `scheduleId`。

### 忙闲查询：用于找空档，不用于代替日程详情

适用场景：
- 创建多人会议前检查冲突
- 用户直接问“我什么时候有空”
- 用户直接问“这几个人何时都有空”
- 需要给出候选会议时间

不适用场景：
- 用户已提供 `scheduleId`，想看某个日程详情
- 用户只是想确认一个具体日程内容

## 参数规则

- `start_ms < end_ms`
- `min_ms < max_ms`
- `search_calendar` 场景下，`start_ms < end_ms`
- `search_calendar` 的 `attendUser` 必填，默认要求用户提供 `mis`；不要主动要求用户提供 `empId`
- `scheduleId` 缺失时，优先先搜索，并直接使用搜索结果中的日程 ID；不要直接向用户追问 `scheduleId`
- 创建和忙闲查询场景里，默认要求用户提供 `mis`；不要主动要求用户提供 `empId`
- 编辑场景里新增/移除参与人默认要求用户提供 `mis`；不要主动要求用户提供 `empId`
- 如果用户只提供人员姓名，除非能从当前上下文准确识别出对应 `mis`，否则必须要求用户补充 `mis`
- 如果 `mis` 解析失败，必须明确告知哪些 `mis` 无法识别，不要带着残缺名单继续创建或查忙闲

## 返回规则

- 脚本默认输出结构化 JSON 或格式化摘要，优先据此总结
- 默认给中文摘要，不贴完整原始 JSON
- 用户态回复里不要展示 `scheduleId`
- 不回传 `email`、`avatar`、内部 ID、`empId`
- 创建确认和忙闲查询时只显示 `mis`；详情查询里的发起人仍优先显示姓名
- 搜索结果优先显示标题、时间、地点、发起人；不要展示 `empId`
- 毫秒时间戳先转北京时间 `YYYY-MM-DD HH:mm` 再回复
- 用户要求创建循环日程时，统一回复“当前暂不支持创建循环日程，后续会继续优化”，不要追问周期规则
- 用户要求会议室日程时，统一回复“当前暂不支持会议室日程，后续会继续优化”，不要追问会议室细节
- 当搜索对象包含其他用户时，回复里要明确说明：结果是你与对方共有、且你当前有权限查看的日程，不代表对方全部日程

### 查询详情输出模板

```text
《{title}》
时间：{startLocal} - {endLocal}
地点：{location 或 无}
提醒：开始前 {reminderMinutesBeforeStart} 分钟
备注：{memo 或 无}
发起人：{organizerName 或 organizerMis}
参与人：{attendeeMis，空则写 无}
```

规则：
- 发起人只显示姓名；没有姓名时显示 `mis`。
- 参与人显示 `mis` 列表，不显示 `empId`。
- 不显示 `empId`，即使返回里带了 `id` 字段也不展示。
- 不显示 `scheduleId`。
- 若 `scheduleId` 非法或查不到数据，不按模板渲染，直接友好提示“未查询到对应日程，可能数据不存在或已失效。”

### 忙闲查询输出模板

单人：

```text
{mis} 的忙碌时间：
- {start1} - {end1}
- {start2} - {end2}
```

多人：

```text
忙碌时间如下：
- {mis1}：{start1} - {end1}；{start2} - {end2}
- {mis2}：{start1} - {end1}
```

空结果：

```text
在 {windowStart} - {windowEnd} 之间，{mis} 没有忙碌时段。
```

规则：
- 忙闲查询只展示 `mis`，不展示姓名或 `empId`。
- 不贴原始数组结构。
- 若用户要求“找可用时间”，需要基于忙碌区间反推出空闲区间后再答复。

### 搜索列表输出模板

```text
在 {windowStart} - {windowEnd} 内，共搜索到 {count} 条日程：
- 《{title1}》
  时间：{start1} - {end1}
  地点：{location1 或 无}
  发起人：{organizer1 或 未知}
```

查询对象包含其他用户时，可改写为：

```text
在 {windowStart} - {windowEnd} 内，共搜索到 {count} 条你与 {misList} 共有、且你当前有权限查看的日程：
- 《{title1}》
  时间：{start1} - {end1}
  地点：{location1 或 无}
  发起人：{organizer1 或 未知}
```

空结果：

```text
在 {windowStart} - {windowEnd} 内，未搜索到参与人包含 {misList} 的日程。
```

规则：
- 不展示 `empId`。
- 不主动展示 `scheduleId`。
- 若后续要查某条详情，可基于搜索结果在内部继续串行调用详情查询，直接使用搜索结果中的日程 ID 作为 `scheduleId`，不要向用户索要。
- 当查询对象包含其他用户时，要明确说明结果不是对方全部日程，而是你与对方共有、且你当前有权限查看的日程。

## 常见错误处理

- `CALENDAR_LOGIN_MIS is required when SCHEDULE_AUTH_TOKEN is not set`：未配置登录 mis，先补 `CALENDAR_LOGIN_MIS`
- `failed to obtain token from calendar.sh`：`calendar.sh` 没成功拿到 `COOKIE_DATA`，先检查脚本执行结果
- `No valid session ID provided` / `cannot find session id`：说明没走脚本或握手失败，重新执行脚本
- `50910 introspect token error`：token 无效或过期，提醒用户更新 token
- `30002 标准开放能力权限校验失败`：当前 token 没有对应工具权限，提示用户补齐权限或重新授权
- `mis lookup failed`：有 `mis` 无法转换成 `empId`，需要向用户确认正确 mis
- `search_calendar` 入参校验失败：优先检查 `attendUser`、`startTime`、`endTime`、`tid` 是否齐全且类型正确
- `Invalid origin`：服务端 origin 白名单问题
- `tool call timeout`：网络或服务端超时，可重试 1 次
- 解析失败：先给用户简明失败说明，再附最小必要原文排障

## 推荐追问

- “请确认开始和结束时间，我会先转成毫秒时间戳再执行。”
- “请提供参与人的 mis，多个用逗号分隔；不用给我 empId。”
- “当前只支持通过 mis 查询人员；如果你给的是姓名，请补充对应的 mis。”
- “你是要直接创建，还是先帮你查这几个人什么时候有空？”
- “你是想看某个日程详情，还是想查这段时间的忙闲分布？”

循环日程场景固定回复：

- “当前暂不支持创建循环日程，后续会继续优化。”

会议室日程场景固定回复：

- “当前暂不支持会议室日程，后续会继续优化。”
