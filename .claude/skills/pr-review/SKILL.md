# PR Review 自动化 Skill

## When to use
- 用户要求 review 一个 PR
- 用户说"帮我看看这个 PR"
- 用户发送 PR 链接

## When not to use
- 用户只是要查看 PR 列表（用 mtcode list）
- 用户要创建 PR（用 mpr create）
- 用户要合并 PR（用 mpr merge）

## Required inputs
- PR 链接或 PR 编号
- （可选）重点关注的方面：性能、安全、逻辑、代码风格等

## Procedure

### Phase 1: 获取 PR 信息
```bash
# 从 PR URL 提取项目名和 PR 编号
# 或直接使用用户提供的 PR 编号

# 获取 PR 详情
mtcode pr get <project> <pr_number>

# 获取 PR 的文件变更列表
mtcode pr diff <project> <pr_number>
```

### Phase 2: 分析代码变更
1. 读取变更的文件列表
2. 对每个变更文件：
   - 分析变更类型：新增/修改/删除
   - 识别关键变更点
   - 标记需要重点关注的代码

### Phase 3: 深度分析（可选）
对于复杂的变更，使用 CatPaw Claude Code 进行深度分析：
```bash
mc --code "分析这个变更：<变更内容>，重点关注：<用户指定的方面>"
```

### Phase 4: 输出 Review 结果
按以下结构输出：

```markdown
## PR Review 报告

**PR 编号**: #xxx
**标题**: xxx
**作者**: xxx
**变更文件数**: xx 个

### 📊 变更概览
- 新增文件：xx 个
- 修改文件：xx 个
- 删除文件：xx 个
- 变更行数：+xxx / -xxx

### 🔍 详细分析

#### 文件 1: `path/to/file.java`
**变更类型**: 修改
**风险等级**: 🔴 高 / 🟡 中 / 🟢 低

**变更内容**:
- ...

**潜在问题**:
1. xxx
2. xxx

**建议**:
- xxx

#### 文件 2: ...

### ⚠️ 需要关注的点
1. **P0 (必须修改)**: xxx
2. **P1 (建议修改)**: xxx
3. **P2 (可选优化)**: xxx

### 💡 总体评价
- 代码质量：⭐⭐⭐⭐
- 可维护性：⭐⭐⭐
- 风险程度：中等
- 建议：xxx
```

## Output format
- Markdown 格式的 Review 报告
- 包含 P0/P1/P2 分级的问题列表
- 给出明确的建议和结论

## Failure handling
1. 如果 PR 不存在或无权限访问 → 告知用户原因
2. 如果 diff 太大（>5000行）→ 建议分段 review 或只关注关键文件
3. 如果无法获取 PR 信息 → 检查登录状态，提示用户重新认证

## Examples

### Example 1: 基本 Review
用户：帮我 review 这个 PR https://code.sankuai.com/waimai/order-after-sale/-/merge_requests/1234

助手：
1. 提取项目：waimai/order-after-sale，PR 编号：1234
2. 执行 `mtcode pr get` 获取详情
3. 执行 `mtcode pr diff` 获取变更
4. 分析并输出报告

### Example 2: 关注特定方面
用户：review 这个 PR，重点关注性能问题
[PR 链接]

助手：
1. 获取 PR 信息
2. 重点分析可能影响性能的代码：
   - 循环中的数据库查询
   - 大对象创建
   - 缓存使用
   - 算法复杂度
3. 输出性能专项 Review 报告
