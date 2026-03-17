# 周报自动生成 Skill

## When to use
- 用户说"帮我写周报"
- 用户说"生成周报"
- 用户说"这周干了什么"
- 定时任务每周五自动触发

## When not to use
- 用户只是要查看日程
- 用户要写日报（用另一个 Skill）

## Required inputs
- （可选）时间范围：默认本周一到现在
- （可选）重点关注的项目或方向

## Procedure

### Phase 1: 数据收集
自动从以下来源收集本周工作内容：

1. **Git 提交记录**
```bash
# 获取本周提交
git log --since="monday" --oneline --author="$(git config user.name)"

# 按项目分类
git log --since="monday" --oneline --author="$(git config user.name)" --format="%s" | sort | uniq
```

2. **PR Review 记录**
```bash
# 通过 mtcode 获取
mtcode pr list --reviewer me --since monday
```

3. **工单处理记录**
```bash
# 通过 TT 系统获取
tt list --handler me --since monday
```

4. **日程/会议记录**
- 通过 calendar-manager skill 获取本周会议

5. **学城文档贡献**
- 通过 citadel skill 获取本周编辑的文档

### Phase 2: 内容整理
按以下维度整理：

1. **重点项目进展**
   - 完成的功能
   - 推进的项目
   - 遇到的问题

2. **日常事务**
   - Bug 修复
   - PR Review
   - 会议参与

3. **学习成长**
   - 学习的新技术
   - 分享的知识

4. **下周计划**
   - 待完成事项
   - 计划推进的项目

### Phase 3: 生成周报
```markdown
# 周报 - YYYY-MM-DD

## 📋 本周工作总结

### 重点项目

#### 1. [项目名称]
**进展**: 已完成 xx%，本周完成 xxx
**关键产出**:
- PR: #123, #124
- 文档: [链接]

#### 2. [项目名称]
**进展**: ...

### 日常事务
- ✅ 完成 PR Review: xx 个
- ✅ 处理工单: xx 个
- ✅ 参与会议: xx 个

### 📊 数据统计
| 指标 | 本周 | 环比 |
|------|------|------|
| 代码提交 | xx 次 | ↑xx% |
| PR Review | xx 个 | — |
| 工单处理 | xx 个 | ↑xx% |

### ⚠️ 遇到的问题
1. xxx
   - 影响: xxx
   - 解决方案: xxx

### 📚 学习成长
- 学习了 xxx
- 分享了 xxx

### 📅 下周计划
1. [ ] 完成 xxx
2. [ ] 推进 xxx
3. [ ] 跟进 xxx

### 💡 需要协调的事项
- xxx 需要 xxx 支持
- xxx 需要 xxx 确认
```

## Output format
- Markdown 格式的周报
- 自动发送到大象或企业微信（可选）
- 保存到 `memory/weekly-reports/YYYY-Wxx.md`

## 定时任务配置
在 `HEARTBEAT.md` 或 Cron 中配置：
```
每周五 17:00 自动生成周报
```

## Examples

### Example 1: 手动生成
用户：帮我写个周报

助手：
1. 收集本周 Git 提交、PR、工单、会议
2. 整理并生成周报
3. 询问是否需要发送或保存

### Example 2: 定时生成
系统自动在周五 17:00 触发，生成周报并推送到企业微信。

## Notes
- 周报内容需要用户确认后再发送
- 敏感信息需要脱敏处理
- 可以配置不同的周报模板（技术/产品/管理）
