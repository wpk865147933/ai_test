# DOM 选择器参考

大象网页版 (x.sankuai.com) 的 CSS 选择器集中维护。大象前端改版时只需更新此文件和对应 scripts/。

## 搜索

| 名称 | 选择器 | 说明 |
|------|--------|------|
| 搜索框 | `.Auto_SearchInput` | 全局搜索输入框，所有页面顶部可用 |
| 群聊结果项 | `.suggest-item-group` | 搜索下拉中的群聊条目 |
| 个人结果项 | `.suggest-item-user`, `.suggest-item[class*="user"]` | 搜索下拉中的个人条目 |
| 结果名称 | `.name-line` | 搜索结果中的名称文本 |

## 聊天记录面板

| 名称 | 选择器 | 说明 |
|------|--------|------|
| 打开面板按钮 | `.Auto_SearchHistoryBtn` | 聊天记录搜索按钮 |
| 面板容器 | `.wrapper_chatMsgSearch_panel` | 聊天记录面板根元素，用于检测面板是否打开 |
| 关键词输入框 | `input.keyword-input` | 消息内容关键词筛选，输入后按 Enter 触发搜索 |
| 发送人选择器 | `.select-sender` | 发送人下拉选择框，点击展开群成员列表 |
| 发送人下拉项 | `.rc-select-dropdown-menu-item.search-item` | 下拉列表中的单个成员项，点击选中 |
| 发送人已选标签 | `.rc-select-selection__choice` | 已选中的发送人标签 |
| 发送人移除按钮 | `.rc-select-selection__choice__remove` | 点击取消已选发送人 |
| 日期选择器 | `.wrapper_chatMsgSearch_panel .datePicker-input` | 日期范围输入框 |
| 日期清除按钮 | `.datePicker-input-clear` | 点击重置日期范围为空 |
| 日历单元格 | `td.rc-calendar-cell[title="{日期}"]` | title 格式：`2026年3月2日` |
| 日历日期文本 | `.rc-calendar-date` | 日历单元格内的可点击元素 |
| 日历月份标题 | `.rc-calendar-my-select` | 显示当前年月，点击可展开月份选择面板 |
| 月份选择面板 | `.rc-calendar-month-panel` | 月份选择面板容器 |
| 月份选择项 | `.rc-calendar-month-panel-cell` | 月份选择单元格，data-value 格式：`2026-02` |
| 月份选择文本 | `.rc-calendar-month-panel-month` | 月份单元格内的可点击元素 |
| 日历左箭头（上月） | `.rc-calendar-prev-month-btn` | 切换到上一个月 |
| 日历右箭头（下月） | `.rc-calendar-next-month-btn` | 切换到下一个月 |

## 消息列表

| 名称 | 选择器 | 说明 |
|------|--------|------|
| 消息列表容器 | `.wrapper_chatMsgSearch_panel .chat-msg-list` | 消息列表根元素 |
| 按天分组 | `.day-msg-list` | 每天的消息分组容器 |
| 天标题 | `.split-line .day` | 日期分隔线中的日期文本 |
| 单条消息 | `.msg-item` | 单条消息项 |
| 发送者姓名 | `.info .name` | 消息发送者姓名 |
| 发送者 MIS | `.info .mis` | 消息发送者 MIS 号 |
| 发送时间 | `.info .time` | 消息发送时间 |
| 文本消息内容 | `.dx-message-text` | 纯文本消息内容元素 |
| 非文本消息内容 | `.message-inner` | 卡片/链接等非文本消息的容器 |

## 发送

| 名称 | 选择器 | 说明 |
|------|--------|------|
| 消息输入框 | `#textTextarea` | 纯文本消息输入框 |
| 发送按钮 | `div.ctn-send-msg-btn button.send-message-button` | 发送消息按钮 |
